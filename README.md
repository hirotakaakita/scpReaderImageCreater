# SCP Reader Comic Generator

SCP記事を題材に、多言語のコマ漫画を生成してSCP Readerアプリ / 紹介botから参照するリポジトリです。エージェント運用は **Codexのみ**。常設ルールは `AGENTS.md`、漫画仕様は `docs/comic-spec.md`、タスク別手順は `.agents/skills/` を参照してください。

## 基本方針

- 台本は `comics/queue/scp-XXX.yaml`。
- **漫画本文は原則 Description のみから構成**します。
- Special Containment Procedures を使うのは例外で、Descriptionで構成した1〜3コマ目を受ける自然な「結」になる場合の **4コマ目のみ**です。
- 画像には文字を描かせず、Pythonが15言語のcaption/title/footerを後から合成します。
- 画像生成は現状ローカルComfyUI。ChatGPT画像生成へ渡す場合は `$scp-chatgpt-image-handoff` を使います。
- 生成画像は候補を目視確認して採用します。

## Codex workflow

- `$write-scp-script` — live記事を確認して台本作成
- `$review-scp-script` — source/scene/caption/起承転結レビュー
- `$prepare-scp-comic` — review → mock → prompt export
- `$refine-panel` — 生成画像を見ながら1コマを改善
- `$revise-comic-text` — 人間レビュー後の文章修正。意味を変える場合は**15言語すべて同時更新**
- `$scp-chatgpt-image-handoff` — ChatGPT画像生成へ固定1:1画像としてhandoff

## Pipeline

```text
comics/queue/scp-XXX.yaml
        ↓
scripts/generate_panels.py
        ↓
output/scp-XXX/panels_temp/       # variants
        ↓
scripts/select_variant.py         # 採用 + provenance + 720x720正規化
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

ComfyUI利用時は `scripts/providers/comfyui/README.md` に従ってモデル/LoRAを配置し、ローカルAPIを起動します。

## Generate candidates

```bash
python scripts/run_pipeline.py --id scp-999 --variants 4
```

候補は `output/scp-999/panels_temp/panel_N_vM.png` に生成されます。ComfyUIはQwenのnative square解像度で生成しますが、採用時に最終コマ寸法へ正規化します。

候補を採用するときは手動copyではなく:

```bash
python scripts/select_variant.py --id scp-999 --panel 1 --variant 3
```

を使ってください。`selected.json` にprompt/scene/seed/元画像サイズ/採用サイズを残し、採用画像を `config/layout.yaml` の固定サイズ（現在720x720）へ中央crop + resizeします。

全コマを選んだら:

```bash
python scripts/run_pipeline.py --id scp-999 --skip-generate
```

15言語合成後、publish gateを通った場合だけdone/used/indexへ進みます。

## Mock

```bash
python scripts/run_pipeline.py --id scp-999 --mock
```

mockはproductionと同じpanel pathへplaceholderを書けるため、採用済み未コミット画像がある作品に対して不用意に全コマmockを実行しないでください。1コマ確認では `--panel N` を付けます。

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
- ComfyUI native generation: square 1328x1328（採用時に720x720へ正規化）
- ChatGPT image handoff: 1:1を明示し、accepted targetを720x720として扱う。非正方形で返った場合は単一画像自体を中央crop+resizeし、page画像から切り出さない。

## Index API

`index.json` は `schemaVersion` と `generatedAt` を持ちます。アプリ側は将来のschema変更に備えて `schemaVersion` を確認できる構造にしてください。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

## License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
