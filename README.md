# SCP Reader Comic Generator

SCP記事を題材に、多言語のコマ漫画を生成してSCP Readerアプリ / 紹介botから参照するリポジトリです。エージェント運用は **Codexのみ**。常設ルールは `AGENTS.md`、漫画仕様は `docs/comic-spec.md`、タスク別手順は `.agents/skills/` を参照してください。

このリポジトリは画像生成APIを直接呼びません。画像生成は ChatGPT 画像生成（`imagegen`）などの外部ツールで行い、Pythonはprompt生成、外部生成画像の取り込み、正規化、合成、15言語テキスト埋め込み、publish gateを担当します。

## 基本方針

- 台本は `comics/queue/scp-XXX.yaml`。
- **漫画本文は原則 Description のみから構成**します。
- Special Containment Procedures を使うのは例外で、Descriptionで構成した1〜3コマ目を受ける自然な「結」になる場合の **4コマ目のみ**です。
- 画像には文字を描かせず、Pythonがcaption/title/footerを後から合成します。
- 画像は1コマにつき1枚、正方形で生成します。ページ・グリッド・枠・吹き出し・文字入り画像は使いません。

## User-facing Codex skills

普段の運用はこの3つを中心にします。

| 依頼 | Skill | 何をするか |
|---|---|---|
| 台本作成 | `$make-scp-comic-script` | live記事確認 → Description優先台本 → internal review → YAML validation |
| 画像生成 | `$generate-scp-comic-images` | prompt export → panelごとの `imagegen` 依頼/生成 → raw画像パス整理 |
| 生成済み画像取り込み漫画完成 | `$finalize-scp-comic` | `accept_external_panel.py` → 720x720正規化 → 15言語embed → publish check |

文章だけ修正する場合は `$revise-comic-text` を使います。意味が変わる修正は15言語すべてを同時に更新します。

## Recommended requests to Codex

### 1. 台本作成

```text
scp-173 の漫画台本を作ってください。
AGENTS.md を読み、$make-scp-comic-script の手順で進めてください。
画像生成はまだしないでください。
```

### 2. 画像生成

```text
scp-173 の画像を生成してください。
AGENTS.md を読み、$generate-scp-comic-images の手順で進めてください。
ChatGPT画像生成（imagegen）を使い、1コマにつき1枚の正方形画像を生成してください。
漫画ページ、複数コマ、文字、吹き出し、枠は生成しないでください。
完成処理はまだしないでください。
```

### 3. 生成済み画像取り込み漫画完成

```text
scp-173 の生成済み画像を取り込んで漫画を完成させてください。
AGENTS.md を読み、$finalize-scp-comic の手順で進めてください。

画像:
- panel 1: ./panel_1.png
- panel 2: ./panel_2.png
- panel 3: ./panel_3.png
- panel 4: ./panel_4.png
```

## Pipeline

```text
Codex: $make-scp-comic-script
  ↓
comics/queue/scp-XXX.yaml
  ↓
Python validation
  ↓
Codex: $generate-scp-comic-images
  ↓
python scripts/run_pipeline.py --id scp-XXX --export-prompts
  ↓
output/scp-XXX/prompts/panel_N.txt
  ↓
ChatGPT image generation (`imagegen`)
  ↓
output/scp-XXX/panels_temp/panel_N_imagegen_vM.png  # raw/debug, gitignored
  ↓
Codex/Python: $finalize-scp-comic
  ↓
python scripts/accept_external_panel.py
  ↓
output/scp-XXX/panels/panel_N.png  # accepted 720x720 source panels
  ↓
python scripts/run_pipeline.py --id scp-XXX --skip-generate
  ↓
output/scp-XXX/base.png
output/scp-XXX/thumbnail.png       # accepted panel_1.png から直接生成
output/scp-XXX/<lang>.png          # 15 languages
output/scp-XXX/meta.json
  ↓
python scripts/publish_check.py scp-XXX
  ↓
index.json / state/used.json / comics/done/
```

`thumbnail.png` は **`panels/panel_1.png` から直接**作ります。`base.png`、`generated-page.png`、その他ページ合成画像から切り出してはいけません。これにより漫画の余白・枠・caption領域がサムネイルへ混入するのを防ぎます。

`generated-page.png` はproduction pipelineでは生成も参照もしません。外部handoff処理がpreview/debug用に作った場合もdisposable artifactとして扱い、thumbnail/panelの入力にしないでください。

## Setup

```bash
pip install -r requirements.txt
python scripts/download_fonts.py
pytest -q
python scripts/validate_scripts.py --all
```

## Script validation

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml
python scripts/validate_scripts.py --all
```

YAML構造、15言語caption、character key、caption position、source section policyなどを検証します。画像生成やoutput更新は行いません。

## Prompt export

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

`output/scp-XXX/prompts/` に各コマのprompt、manifest、参照画像が書き出されます。

## imagegen request template

各 `panel_N.txt` を使い、ChatGPT画像生成（`imagegen`）に1コマずつ依頼します。

```text
Generate a single image for one SCP comic panel.

Hard requirements:
- Use a square 1:1 canvas.
- Produce exactly one standalone illustration for panel N.
- Do not create a comic page, four-panel strip, storyboard, grid, border, or split-screen layout.
- Do not render any text, letters, numbers, captions, signs, labels, sound effects, watermarks, speech bubbles, or thought bubbles.
- Draw one continuous moment only.
- Keep important faces, hands, and props away from the outer edge because the accepted image will be center-cropped/resized to 720x720 if needed.

Use this project prompt exactly as the semantic/art direction:

<contents of output/scp-XXX/prompts/panel_N.txt>
```

`imagegen` が返した画像は、できれば以下に保存します。

```text
output/scp-XXX/panels_temp/panel_N_imagegen_vM.png
```

`panels_temp/` はgitignore済みです。保存先が違っても、次の取り込み時に `--source` で渡せば問題ありません。

## Accept generated panels

```bash
python scripts/accept_external_panel.py --id scp-XXX --panel 1 --source /path/to/panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 2 --source /path/to/panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 4 --source /path/to/panel_4.png --provider imagegen
```

取り込み時に、元画像は `panels_temp/` にコピーされ、accepted panelは `output/scp-XXX/panels/panel_N.png` に720x720で保存されます。`selected.json` にはprompt/scene/provider/元画像サイズ/採用サイズ/正規化方法が残ります。

## Compose, embed, and publish check

全コマを採用したら:

```bash
python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX
```

`--skip-generate` は画像生成を行わず、accepted panelsを使って合成・15言語embed・publish gate・index更新を行います。最終publication runでは `--languages ja` のような部分実行を使わないでください。

## Mock

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

mockはproductionと同じpanel pathへplaceholderを書けるため、採用済み未コミット画像がある作品に対して不用意に全コマmockを実行しないでください。1コマ確認では `--panel N` を付けます。

`--variants` は現在mock専用です。実画像の候補生成には使いません。

## Text revision after human review

人間レビュー後にcaption等を直す場合は `$revise-comic-text` を使います。意味が変わる修正はja/enだけで済ませず、**ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant の全言語を更新**します。

修正後は画像を再生成せず:

```bash
python scripts/validate_scripts.py comics/done/scp-XXX.yaml
python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX
```

として全言語を再embedします。

## Image sizes

- accepted panel: `config/layout.yaml`（現在 **720x720**）
- thumbnail: 現在 **480x480**
- imagegen/external handoff: 1:1を明示し、accepted targetを720x720として扱う。非正方形で返った場合は単一画像自体を中央crop+resizeし、page画像から切り出さない。

## Index API

`index.json` は `schemaVersion` と `generatedAt` を持ちます。アプリ側は将来のschema変更に備えて `schemaVersion` を確認できる構造にしてください。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

## License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
