"""パイプライン一括実行（GitHub Actionsのエントリポイント）。

  python scripts/run_pipeline.py --from-queue            # キュー先頭を1本処理
  python scripts/run_pipeline.py --from-queue --count 2
  python scripts/run_pipeline.py --id scp-999            # 指定台本を(再)処理
  python scripts/run_pipeline.py --id scp-999 --skip-generate --mock  # 合成以降のみ

処理内容: 生成(generate_panels) -> 合成(compose) -> 言語別埋め込み(embed_text)
          -> 台本をdone/へ移動 -> index.json更新
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


def process(script_path, cfgs, mock=False, languages=None, skip_generate=False):
    script = cfglib.load_script(script_path)
    print(f"=== {script['id']} ({script_path}) ===")
    if not skip_generate:
        generate_panels.generate(script, cfgs, mock=mock)
    compose.compose(script, cfgs)
    embed_text.embed(script, cfgs, languages=languages)
    # 成功したらキューからdoneへ（mock実行では動かさない）
    if not mock and not skip_generate and \
            os.path.dirname(os.path.abspath(script_path)) == os.path.abspath(cfglib.QUEUE_DIR):
        os.makedirs(cfglib.DONE_DIR, exist_ok=True)
        shutil.move(script_path, os.path.join(cfglib.DONE_DIR, os.path.basename(script_path)))
        print(f"[queue] moved to done/: {os.path.basename(script_path)}")


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
    args = ap.parse_args()

    cfgs = cfglib.load_configs()
    langs = args.languages.split(",") if args.languages else None

    if args.comic_id:
        targets = [find_script(args.comic_id)]
    else:
        targets = queued_scripts()[: args.count]
        if not targets:
            print("Queue is empty. Nothing to do.")
            return

    if not args.mock and not args.skip_generate and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY is not set (use --mock for a dry run)")
        sys.exit(1)

    for path in targets:
        process(path, cfgs, mock=args.mock, languages=langs,
                skip_generate=args.skip_generate)
    build_index.build()


if __name__ == "__main__":
    main()
