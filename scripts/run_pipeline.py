"""パイプライン一括実行（ローカルで手動実行する）。"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import build_index  # noqa: E402
import compose  # noqa: E402
import embed_text  # noqa: E402
import generate_panels  # noqa: E402
import publish_check  # noqa: E402


def find_script(comic_id):
    for d in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
        path = os.path.join(d, f"{comic_id}.yaml")
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"script not found for id: {comic_id}")


def queued_scripts():
    if not os.path.isdir(cfglib.QUEUE_DIR):
        return []
    return sorted(os.path.join(cfglib.QUEUE_DIR, f) for f in os.listdir(cfglib.QUEUE_DIR)
                  if f.endswith(".yaml") or f.endswith(".yml"))


def move_to_done(script_path):
    os.makedirs(cfglib.DONE_DIR, exist_ok=True)
    dest = os.path.join(cfglib.DONE_DIR, os.path.basename(script_path))
    n = 1
    while os.path.exists(dest):
        stem, ext = os.path.splitext(os.path.basename(script_path))
        dest = os.path.join(cfglib.DONE_DIR, f"{stem}-dup{n}{ext}")
        n += 1
    shutil.move(script_path, dest)
    print(f"[queue] moved to done/: {os.path.basename(dest)}")


def process(script_path, cfgs, mock=False, languages=None, skip_generate=False,
            export_prompts=False, variants=None, panel=None):
    script = cfglib.load_script(script_path)
    print(f"=== {script['id']} ({script_path}) ===")
    if export_prompts:
        generate_panels.export_prompts(script, cfgs)
        return
    if variants:
        generate_panels.generate_variants(script, cfgs, variants, mock=mock, panel=panel)
        return
    if not skip_generate:
        generate_panels.generate(script, cfgs, mock=mock, panel=panel)
    compose.compose(script, cfgs)
    embed_result = embed_text.embed(script, cfgs, languages=languages)

    if not mock:
        gate_errors = publish_check.check(script["id"]) if embed_result.get("complete") is True else [
            "embed result is not explicitly publish-complete"]
        if gate_errors:
            print(f"[state] WARN: {script['id']} is NOT publish-ready; NOT moved to done/ "
                  "and NOT recorded in used.json")
            for error in gate_errors:
                print(f"  - {error}")
        else:
            if os.path.dirname(os.path.abspath(script_path)) == os.path.abspath(cfglib.QUEUE_DIR):
                move_to_done(script_path)
            cfglib.mark_used(script["id"])
            print(f"[state] publish gate passed; recorded in used.json: {script['id']}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-queue", action="store_true")
    g.add_argument("--id", dest="comic_id", help="カンマ区切りで複数指定可")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--mock", action="store_true",
                    help="APIを呼ばずplaceholder panelを生成してlayout/textを検証する")
    ap.add_argument("--languages", help="カンマ区切りで対象言語を限定 (例: ja,en)")
    ap.add_argument("--skip-generate", action="store_true",
                    help="画像生成を行わず、accepted panelsから合成・埋め込みだけ行う")
    ap.add_argument("--export-prompts", action="store_true",
                    help="外部画像生成向けにプロンプト・参照画像を書き出す")
    ap.add_argument("--variants", type=int,
                    help="mock候補だけをpanels_temp/に生成する。実画像生成には使わない")
    ap.add_argument("--panel", type=int)
    args = ap.parse_args()

    if args.variants is not None and args.variants <= 0:
        ap.error(f"--variants must be a positive integer (got {args.variants})")
    if args.variants is not None and not args.mock:
        ap.error("--variants is mock-only because local image providers were removed. "
                 "Use --export-prompts, generate images externally, then run "
                 "scripts/accept_external_panel.py for each accepted image.")
    if args.count <= 0:
        ap.error(f"--count must be a positive integer (got {args.count})")

    cfgs = cfglib.load_configs()
    langs = args.languages.split(",") if args.languages else None
    if langs:
        allowed = set(cfgs["languages"]["languages"])
        unknown = [lang for lang in langs if lang not in allowed]
        if unknown:
            ap.error(f"unknown language(s): {', '.join(unknown)}")

    if args.comic_id:
        comic_ids = [c.strip() for c in args.comic_id.split(",") if c.strip()]
        for i, comic_id in enumerate(comic_ids, 1):
            if len(comic_ids) > 1:
                print(f"--- [{i}/{len(comic_ids)}] {comic_id} ---")
            process(find_script(comic_id), cfgs, mock=args.mock, languages=langs,
                    skip_generate=args.skip_generate, export_prompts=args.export_prompts,
                    variants=args.variants, panel=args.panel)
    else:
        queue = queued_scripts()
        if not queue:
            print("Queue is empty. Nothing to do.")
            return
        used = cfglib.load_used()
        processed = 0
        for path in queue:
            if processed >= args.count:
                break
            script = cfglib.load_script(path)
            if script["id"] in used and not script.get("regenerate"):
                print(f"[skip] {script['id']} is already generated (state/used.json)")
                if not args.mock:
                    move_to_done(path)
                continue
            process(path, cfgs, mock=args.mock, languages=langs,
                    skip_generate=args.skip_generate, export_prompts=args.export_prompts,
                    variants=args.variants, panel=args.panel)
            processed += 1
        if processed == 0:
            print("No unprocessed scripts in queue. Nothing generated.")

    if not args.export_prompts and not args.variants and not args.mock:
        build_index.build()


if __name__ == "__main__":
    main()
