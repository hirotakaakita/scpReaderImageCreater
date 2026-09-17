# SCP Reader Comic Generator

SCP記事を題材に、多言語のコマ漫画を生成してSCP Readerアプリ / 紹介botから参照するリポジトリです。エージェント運用は **Codexのみ**。常設ルールは `AGENTS.md`、漫画仕様は `docs/comic-spec.md`、タスク別手順は `.agents/skills/` を参照してください。

## 基本方針

- 台本は `comics/queue/scp-XXX.yaml`。
- **漫画本文は原則 Description のみから構成**します。
- Special Containment Procedures を使うのは例外で、Descriptionで構成した1〜3コマ目を受ける自然な「結」になる場合の **4コマ目のみ**です。
- このリポジトリは画像生成APIを直接呼びません。Codex/Pythonはプロンプト生成、外部生成画像の取り込み、合成、15言語テキスト埋め込み、publish gateを担当します。
- 画像には文字を描かせず、Pythonがcaption/title/footerを後から合成します。
- 外部画像生成は `$scp-chatgpt-image-handoff` の固定1:1ルールで行い、受け取った画像を `scripts/accept_external_panel.py` で採用します。

## Codex workflow

- `$write-scp-script` — live記事を確認して台本作成
- `$review-scp-script` — source/scene/caption/起承転結レビュー
- `$prepare-scp-comic` — review → mock → external prompt export
- `$refine-panel` — 生成画像を見ながら1コマを改善。再生成は外部画像生成で行う
- `$revise-comic-text` — 人間レビュー後の文章修正。意味を変える場合は**15言語すべて同時更新**
- `$scp-chatgpt-image-handoff` — ChatGPT画像生成等へ固定1:1画像としてhandoff

## Pipeline

```text
comics/queue/scp-XXX.yaml
        ↓
scripts/generate_panels.py --export-prompts
        ↓
output/scp-XXX/prompts/panel_N.txt
        ↓
外部画像生成（ChatGPT等。1枚=1コマ、1:1）
        ↓
scripts/accept_external_panel.py  # 採用 + provenance + 720x720正規化
        ↓
output/scp-XXX/panels/panel_N.png # accepted source panels
        ↓
scripts/compose.py
        ├─ base.png
        └─ thumbnail.png           # accepted panel_1.png から直接生成
        ↓
scripts/embed_text.py             # 15言語
        ↓
scripts/publish_check.py          # deterministic publish gate
        ↓
index.json
```

`thumbnail.png` は **`panels/panel_1.png` から直接**作ります。`base.png`、`generated-page.png`、その他ページ合成画像から切り出してはいけません。これにより漫画の余白・枠・caption領域がサムネイルへ混入するのを防ぎます。

`generated-page.png` は現在のproduction pipelineでは生成も参照もしません。外部の画像handoff処理がpreview/debug用に作った場合もdisposable artifactとして扱い、thumbnail/panelの入力にしないでください。

## Setup

```bash
pip install -r requirements.txt
python scripts/download_fonts.py
pytest -q
python scripts/validate_scripts.py --all
```

## Prepare prompts

```bash
python scripts/run_pipeline.py --id scp-999 --export-prompts
```

`output/scp-999/prompts/` に、各コマのprompt、manifest、参照画像が書き出されます。

## Generate images externally

各 `panel_N.txt` を外部画像生成ツールへ渡して、**1コマにつき1枚の正方形画像**を作ります。

要求する画像仕様:

- 1:1 square
- accepted target: 現在 **720x720**
- one continuous moment, not a page/strip/grid
- no caption, no speech bubble, no text, no watermark

外部ツールが720x720以外を返しても、`accept_external_panel.py` が中央crop + resizeでaccepted panelへ正規化します。ページ画像から切り出してはいけません。

## Accept generated panels

```bash
python scripts/accept_external_panel.py --id scp-999 --panel 1 --source /path/to/generated-panel-1.png --provider chatgpt-image
python scripts/accept_external_panel.py --id scp-999 --panel 2 --source /path/to/generated-panel-2.png --provider chatgpt-image
python scripts/accept_external_panel.py --id scp-999 --panel 3 --source /path/to/generated-panel-3.png --provider chatgpt-image
python scripts/accept_external_panel.py --id scp-999 --panel 4 --source /path/to/generated-panel-4.png --provider chatgpt-image
```

採用すると、正規化済み画像が `output/scp-999/panels/panel_N.png` に保存され、`selected.json` にprompt/scene/provider/元画像サイズ/採用サイズ/正規化方法が残ります。

全コマを採用したら:

```bash
python scripts/run_pipeline.py --id scp-999 --skip-generate
```

15言語合成後、publish gateを通った場合だけdone/used/indexへ進みます。

## Mock

```bash
python scripts/run_pipeline.py --id scp-999 --mock
```

mockはproductionと同じpanel pathへplaceholderを書けるため、採用済み未コミット画像がある作品に対して不用意に全コマmockを実行しないでください。1コマ確認では `--panel N` を付けます。

`--variants` は現在mock専用です。実画像の候補生成には使いません。

## Text revision after human review

人間レビュー後にcaption等を直す場合は `$revise-comic-text` を使います。意味が変わる修正はja/enだけで済ませず、**ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant の全言語を更新**します。

修正後は画像を再生成せず:

```bash
python scripts/validate_scripts.py comics/done/scp-XXX.yaml
python scripts/run_pipeline.py --id scp-XXX --skip-generate
```

として全言語を再embedします。`--languages ja` 等の部分実行は最終publication runとして使いません。

## Image sizes

- accepted panel: `config/layout.yaml`（現在 **720x720**）
- thumbnail: 現在 **480x480**
- external image handoff: 1:1を明示し、accepted targetを720x720として扱う。非正方形で返った場合は単一画像自体を中央crop+resizeし、page画像から切り出さない。

## Index API

`index.json` は `schemaVersion` と `generatedAt` を持ちます。アプリ側は将来のschema変更に備えて `schemaVersion` を確認できる構造にしてください。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

## License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
