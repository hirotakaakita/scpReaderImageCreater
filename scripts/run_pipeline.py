"""パイプライン一括実行（GitHub Actionsのエントリポイント）。

  python scripts/run_pipeline.py --from-queue            # キュー先頭を1本処理
  python scripts/run_pipeline.py --from-queue --count 2
  python scripts/run_pipeline.py --id scp-999            # 指定台本を(再)処理
  python scripts/run_pipeline.py --id scp-999 --skip-generate --mock  # 合成以降のみ
  python scripts/run_pipeline.py --id scp-999 --export-prompts  # Google AI Studio向けに書き出し

処理内容: 生成(generate_panels) -> 合成(compose) -> 言語別埋め込み(embed_text)
          -> 台本をdone/へ移動 -> index.json更新

--export-prompts を付けるとAPIを呼ばず、output/<id>/prompts/ にプロンプトと参照画像・
手順書(README.txt)を書き出すだけで終了する。Google AI Studioで手動生成した画像を
output/<id>/panels/panel_N.png として保存したら、--skip-generate で続きを実行する。
"""
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


def find_script(comic_id):
    for d in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
        path = os.path.join(d, f"{comic_id}.yaml")
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"script not found for id: {comic_id}")


def queued_scripts():
    if not os.path.isdir(cfglib.QUEUE_DIR):
        return []
    return sorted(
        os.path.join(cfglib.QUEUE_DIR, f)
        for f in os.listdir(cfglib.QUEUE_DIR)
        if f.endswith(".yaml") or f.endswith(".yml")
    )


def move_to_done(script_path):
    os.makedirs(cfglib.DONE_DIR, exist_ok=True)
    dest = os.path.join(cfglib.DONE_DIR, os.path.basename(script_path))
    n = 1
    while os.path.exists(dest):  # 同名がある場合は上書きせず連番を付ける
        stem, ext = os.path.splitext(os.path.basename(script_path))
        dest = os.path.join(cfglib.DONE_DIR, f"{stem}-dup{n}{ext}")
        n += 1
    shutil.move(script_path, dest)
    print(f"[queue] moved to done/: {os.path.basename(dest)}")


def process(script_path, cfgs, mock=False, languages=None, skip_generate=False,
            export_prompts=False):
    script = cfglib.load_script(script_path)
    print(f"=== {script['id']} ({script_path}) ===")
    if export_prompts:
        generate_panels.export_prompts(script, cfgs)
        return
    if not skip_generate:
        generate_panels.generate(script, cfgs, mock=mock)
    compose.compose(script, cfgs)
    embed_text.embed(script, cfgs, languages=languages)
    # 成功したらキューからdoneへ移し、生成済みとして記録（mock実行では何もしない）
    if not mock and not skip_generate:
        if os.path.dirname(os.path.abspath(script_path)) == os.path.abspath(cfglib.QUEUE_DIR):
            move_to_done(script_path)
        cfglib.mark_used(script["id"])
        print(f"[state] recorded in used.json: {script['id']}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-queue", action="store_true")
    g.add_argument("--id", dest="comic_id")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--mock", action="store_true", help="APIを呼ばずプレースホルダー生成")
    ap.add_argument("--languages", help="カンマ区切りで対象言語を限定 (例: ja,en)")
    ap.add_argument("--skip-generate", action="store_true",
                    help="画像生成を飛ばし合成・埋め込みのみ再実行")
    ap.add_argument("--export-prompts", action="store_true",
                    help="APIを呼ばずGoogle AI Studio向けにプロンプト・参照画像を"
                         "output/<id>/prompts/ に書き出す（合成・埋め込みは行わない）")
    args = ap.parse_args()

    cfgs = cfglib.load_configs()
    langs = args.languages.split(",") if args.languages else None

    if (not args.mock and not args.skip_generate and not args.export_prompts
            and not os.environ.get("GEMINI_API_KEY")):
        print("ERROR: GEMINI_API_KEY is not set (use --mock for a dry run)")
        sys.exit(1)

    if args.comic_id:
        # --id は明示指定なので生成済みでも(再)処理する
        process(find_script(args.comic_id), cfgs, mock=args.mock, languages=langs,
                skip_generate=args.skip_generate, export_prompts=args.export_prompts)
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
            # 生成済みのSCPはスキップ（意図的な再生成は台本に regenerate: true か --id 指定）
            if script["id"] in used and not script.get("regenerate"):
                print(f"[skip] {script['id']} is already generated (state/used.json)")
                if not args.mock:
                    move_to_done(path)
                continue
            process(path, cfgs, mock=args.mock, languages=langs,
                    skip_generate=args.skip_generate, export_prompts=args.export_prompts)
            processed += 1
        if processed == 0:
            print("No unprocessed scripts in queue. Nothing generated.")
    if not args.export_prompts:
        build_index.build()


if __name__ == "__main__":
    main()
