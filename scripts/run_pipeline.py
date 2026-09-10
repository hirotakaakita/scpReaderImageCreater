"""パイプライン一括実行（ローカルで手動実行する）。

  python scripts/run_pipeline.py --from-queue            # キュー先頭を1本処理
  python scripts/run_pipeline.py --from-queue --count 2
  python scripts/run_pipeline.py --id scp-999            # 指定台本を(再)処理
  python scripts/run_pipeline.py --id scp-999,scp-888    # 複数指定（カンマ区切り、1本ずつ順に処理）
  python scripts/run_pipeline.py --id scp-999 --skip-generate --mock  # 合成以降のみ
  python scripts/run_pipeline.py --id scp-999 --export-prompts  # Google AI Studio向けに書き出し
  python scripts/run_pipeline.py --id scp-999 --variants 4      # 選別用に候補を複数生成
  python scripts/run_pipeline.py --id scp-999 --panel 3         # 3コマ目だけ再生成
  python scripts/run_pipeline.py --id scp-999 --panel 3 --variants 4  # 3コマ目だけ候補を追加生成

処理内容: 生成(generate_panels) -> 合成(compose) -> 言語別埋め込み(embed_text)
          -> 台本をdone/へ移動 -> index.json更新

--export-prompts を付けるとAPIを呼ばず、output/<id>/prompts/ にプロンプトと参照画像・
手順書(README.txt)を書き出すだけで終了する。Google AI Studioで手動生成した画像を
output/<id>/panels/panel_N.png として保存したら、--skip-generate で続きを実行する。

--variants N を付けると、コマごとにN枚の候補を output/<id>/panels_temp/panel_N_vM.png
に生成して停止する（panels/panel_N.pngはまだ書き換えない）。人手で気に入った候補を
panels/panel_N.png としてコピーしてから --skip-generate で合成以降を実行する。
生成精度がまだ安定しない間の運用（画像生成の精度がゆらぐ間、複数候補から目視で選ぶ）。
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
            export_prompts=False, variants=None, panel=None):
    script = cfglib.load_script(script_path)
    print(f"=== {script['id']} ({script_path}) ===")
    if export_prompts:
        generate_panels.export_prompts(script, cfgs)
        return
    if variants:
        # 選別用の候補生成のみ行う。panels/はまだ確定していないので
        # 合成・埋め込み・done移動・used.json記録は行わずここで止める
        generate_panels.generate_variants(script, cfgs, variants, mock=mock, panel=panel)
        return
    if not skip_generate:
        generate_panels.generate(script, cfgs, mock=mock, panel=panel)
    compose.compose(script, cfgs)
    embed_result = embed_text.embed(script, cfgs, languages=languages)
    # 成功したらキューからdoneへ移し、生成済みとして記録する（mock実行では何もしない）。
    # ここに到達した時点で合成・埋め込みは完了しているので、--skip-generate
    # （--variantsで候補を選別してから続きを実行する、現状の推奨運用）でも
    # 完成扱いにする。generate()を今回呼んだかどうかは完成状態と無関係
    # （--variantsによる候補生成のみの回はこの手前でreturnしており、ここには来ない）。
    # ただし「例外なく終わった」だけでなく「掲載可能」（文字あふれ・フォント欠落が
    # 無く全言語揃っている）かも見る。complete=Falseの時だけ止める
    # （--languagesで一部言語のみ処理した回はcomplete判定自体を行わないのでNone
    # のまま素通りする＝既存の完成状態を壊さない）
    if not mock:
        if embed_result.get("complete") is False:
            print(f"[state] WARN: {script['id']} is NOT publish-complete "
                  f"(overflow={embed_result['overflow']}, missing_font={embed_result['missing_font']}); "
                  "NOT moved to done/ and NOT recorded in used.json. Fix captions/fonts and rerun.")
        else:
            if os.path.dirname(os.path.abspath(script_path)) == os.path.abspath(cfglib.QUEUE_DIR):
                move_to_done(script_path)
            cfglib.mark_used(script["id"])
            print(f"[state] recorded in used.json: {script['id']}")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-queue", action="store_true")
    g.add_argument("--id", dest="comic_id",
                   help="カンマ区切りで複数指定可（例: scp-999,scp-888）。"
                        "並列ではなく1本ずつ順番に処理する"
                        "（ComfyUIのキューが詰まり空きRAMも逼迫することを確認済みのため）")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--mock", action="store_true", help="APIを呼ばずプレースホルダー生成")
    ap.add_argument("--languages", help="カンマ区切りで対象言語を限定 (例: ja,en)")
    ap.add_argument("--skip-generate", action="store_true",
                    help="画像生成を飛ばし合成・埋め込みのみ再実行")
    ap.add_argument("--export-prompts", action="store_true",
                    help="APIを呼ばずGoogle AI Studio向けにプロンプト・参照画像を"
                         "output/<id>/prompts/ に書き出す（合成・埋め込みは行わない）")
    ap.add_argument("--variants", type=int,
                    help="コマごとにN枚の候補をoutput/<id>/panels_temp/に生成して停止する"
                         "（panels/は書き換えない。選別後にpanels/panel_N.pngへ手動で"
                         "コピーしてから--skip-generateで続きを実行する）")
    ap.add_argument("--panel", type=int,
                    help="指定したコマ番号（1始まり）だけ生成する。省略時は全コマ。"
                         "--variantsと併用可（そのコマだけ候補を追加生成）")
    args = ap.parse_args()

    # --variants 0 はfalsyなので、そのまま通すと process() の `if variants:`
    # 分岐に入らず通常生成に化けて採用済みpanels/を上書きしてしまう。
    # 負数も含めて、指定した場合は正の整数のみ許可する
    if args.variants is not None and args.variants <= 0:
        ap.error(f"--variants must be a positive integer (got {args.variants})")
    if args.count <= 0:
        ap.error(f"--count must be a positive integer (got {args.count})")

    cfgs = cfglib.load_configs()
    langs = args.languages.split(",") if args.languages else None

    if args.comic_id:
        # --id はカンマ区切りで複数指定できる。並列実行はComfyUIのキュー詰まり・
        # 空きRAM逼迫を引き起こすことを確認済みのため、必ず1本ずつ順に処理する。
        # 明示指定なので、生成済み(used.json記載)でも(再)処理する
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
            # 生成済みのSCPはスキップ（意図的な再生成は台本に regenerate: true か --id 指定）
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
    # --mock はプレースホルダー画像・仮のcaption配置での検証run。index.jsonが
    # このrunのmeta.jsonを拾って本番のoutput/<id>/base.png等（mockでも同じ実パスに
    # 書く）をプレースホルダーのまま公開扱いしてしまわないよう、mock時はindex再構築
    # 自体をスキップする（後で本番生成した後に改めてbuild_index.pyを走らせること）
    if not args.export_prompts and not args.variants and not args.mock:
        build_index.build()


if __name__ == "__main__":
    main()
