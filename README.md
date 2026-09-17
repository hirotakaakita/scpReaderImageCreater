# SCP Reader Comic Generator

SCP記事を題材に、多言語のコマ漫画を生成してSCP Readerアプリ / 紹介botから参照するリポジトリです。

エージェント運用は **Codexのみ**。画像生成は ChatGPT 画像生成（`imagegen`）などの外部ツールで行い、このリポジトリは **台本管理・prompt生成・外部生成画像の取り込み・正規化・合成・15言語テキスト埋め込み・publish gate** を担当します。

---

## 重要ルール

- 台本は `comics/queue/scp-XXX.yaml` に作る。
- 漫画本文は原則 **Descriptionのみ** から構成する。
- Special Containment Procedures を使うのは例外。使う場合は、Descriptionで構成した1〜3コマ目を受ける自然な「結」になる場合の **4コマ目のみ**。
- 画像は **1コマにつき1枚**。4コマまとめたページ画像を作らない。
- imagegenには **正方形1:1** を依頼する。
- 画像には文字・caption・吹き出し・枠・ページレイアウトを描かせない。
- 1コマだけ失敗した場合は、そのコマだけ再生成・差し替えする。全コマを再生成しない。
- 意味が変わるテキスト修正は、必ず15言語すべて更新する。
- `output/*/prompts/`、`output/*/panels_temp/`、`output/*/generated-page.png`、`output/*/review-sheet.png` は作業用でコミットしない。

---

## User-facing Codex Skills

普段の運用は、この4つのSkillだけを使います。

| 作業 | Skill | 内容 |
|---|---|---|
| 台本作成 | `$make-scp-comic-script` | live記事確認 → Description優先台本 → internal review → YAML validation |
| 画像生成 | `$generate-scp-comic-images` | prompt export → panelごとの `imagegen` 依頼/生成 → raw画像パス整理。1コマだけの再生成も担当 |
| 生成済み画像取り込み漫画完成 | `$finalize-scp-comic` | `accept_external_panel.py` → 720x720正規化 → 15言語embed → publish check。1コマだけの差し替えも担当 |
| テキスト修正 | `$revise-comic-text` | caption/title/addendum等を修正。意味変更時は15言語すべて更新 |

低レベルSkill（write/review/prepare/refine/handoff）は、上記のユーザー向けSkillに統合済みです。

---

## 最短フロー

新しいSCP漫画を1本作る場合の基本フローです。

```text
1. Codexに台本作成を依頼
   $make-scp-comic-script

2. Codexに画像生成を依頼
   $generate-scp-comic-images

3. imagegenで1コマずつ画像生成
   panel_1.png ... panel_4.png

4. Codexに生成済み画像の取り込み・漫画完成を依頼
   $finalize-scp-comic
```

ローカルコマンドだけで見ると、中心は以下です。

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml
python scripts/run_pipeline.py --id scp-XXX --export-prompts

# imagegenで各panel画像を作成後
python scripts/accept_external_panel.py --id scp-XXX --panel 1 --source /path/to/panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 2 --source /path/to/panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 4 --source /path/to/panel_4.png --provider imagegen

python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX
python scripts/build_review_sheet.py scp-XXX
```

途中状態が分からなくなったら、まずこれを実行します。

```bash
python scripts/comic_status.py scp-XXX
```

---

# 依頼テンプレート集

## 1. 台本作成だけ依頼する

```text
scp-173 の漫画台本を作ってください。
AGENTS.md を読み、$make-scp-comic-script の手順で進めてください。

条件:
- live記事を確認する
- Description優先で4コマにする
- Special Containment Proceduresを使う場合は4コマ目のみ
- source provenance を各panelに入れる
- 15言語captionを作る
- internal reviewを行う
- python scripts/validate_scripts.py comics/queue/scp-173.yaml --strict-source を実行する

画像生成はまだしないでください。
```

成果物:

```text
comics/queue/scp-173.yaml
```

既存台本をまとめて確認するだけなら、後方互換のため通常validationを使います。

```bash
python scripts/validate_scripts.py --all
```

---

## 2. 台本作成からimagegen用prompt出力まで依頼する

```text
scp-173 の漫画を、imagegenで画像生成できるところまで準備してください。
AGENTS.md を読み、以下の流れで進めてください。

1. $make-scp-comic-script で台本作成
2. python scripts/validate_scripts.py comics/queue/scp-173.yaml --strict-source
3. $generate-scp-comic-images でprompt export
4. panelごとの imagegen 依頼文を提示

画像の取り込みと漫画完成はまだしないでください。
```

成果物:

```text
output/scp-173/prompts/panel_1.txt
output/scp-173/prompts/panel_1_imagegen_request.txt
output/scp-173/prompts/panel_2.txt
output/scp-173/prompts/panel_2_imagegen_request.txt
output/scp-173/prompts/panel_3.txt
output/scp-173/prompts/panel_3_imagegen_request.txt
output/scp-173/prompts/panel_4.txt
output/scp-173/prompts/panel_4_imagegen_request.txt
output/scp-173/prompts/manifest.json
output/scp-173/prompts/README.txt
```

`panel_N_imagegen_request.txt` が、そのままChatGPT画像生成へ貼る完成依頼文です。

---

## 3. 全コマ画像生成を依頼する

```text
scp-173 の画像を生成してください。
AGENTS.md を読み、$generate-scp-comic-images の手順で進めてください。

条件:
- ChatGPT画像生成（imagegen）を使う
- 1コマにつき1枚の正方形画像を生成する
- output/scp-173/prompts/panel_N_imagegen_request.txt を使う
- 漫画ページ、複数コマ、grid、frame、border、文字、caption、吹き出しは生成しない
- 生成したraw画像パスを報告する

完成処理はまだしないでください。
```

Codexが実行する基本コマンド:

```bash
python scripts/run_pipeline.py --id scp-173 --export-prompts
```

---

## 4. 1コマだけ画像再生成を依頼する

1コマだけ失敗した場合は、必ずそのコマだけを対象にします。

```text
scp-173 の3コマ目だけ再生成してください。
AGENTS.md を読み、$generate-scp-comic-images の手順で進めてください。

対象:
- panel: 3

理由:
- 既存の3コマ目に文字っぽいものが写っている
- 他のコマはそのまま使う

やること:
- python scripts/comic_status.py scp-173 を実行する
- 既存panel 3と selected.json を確認する
- 必要なら panel 3 の scene だけ修正する
- python scripts/validate_scripts.py comics/queue/scp-173.yaml を実行する
- python scripts/run_pipeline.py --id scp-173 --export-prompts --panel 3 を実行する
- output/scp-173/prompts/panel_3_imagegen_request.txt を使って imagegen でpanel 3だけ生成する
- 生成したraw画像パスを報告する

完成処理はまだしないでください。
```

対応コマンド:

```bash
python scripts/run_pipeline.py --id scp-173 --export-prompts --panel 3
```

---

## 5. 生成済み画像を取り込んで漫画完成を依頼する

```text
scp-173 の生成済み画像を取り込んで漫画を完成させてください。
AGENTS.md を読み、$finalize-scp-comic の手順で進めてください。

画像:
- panel 1: ./panel_1.png
- panel 2: ./panel_2.png
- panel 3: ./panel_3.png
- panel 4: ./panel_4.png

やること:
- scripts/accept_external_panel.py で各panelを取り込む
- python scripts/run_pipeline.py --id scp-173 --skip-generate を実行する
- python scripts/publish_check.py scp-173 を実行する
- python scripts/build_review_sheet.py scp-173 を実行する
- thumbnailに枠やcaptionが混ざっていないか確認する
```

対応コマンド:

```bash
python scripts/accept_external_panel.py --id scp-173 --panel 1 --source ./panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 2 --source ./panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 3 --source ./panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 4 --source ./panel_4.png --provider imagegen
python scripts/run_pipeline.py --id scp-173 --skip-generate
python scripts/publish_check.py scp-173
python scripts/build_review_sheet.py scp-173
```

---

## 6. 画像を一括取り込みする

画像ファイルが `panel_1.png`、`panel_2.png`、... という名前で同じディレクトリにある場合:

```bash
python scripts/accept_external_panel.py --id scp-173 --source-dir ./generated/scp-173 --provider imagegen
```

明示的に対応を指定したい場合はJSON manifestを使います。

```json
{
  "1": "./panel_1.png",
  "2": {"source": "./panel_2.png", "note": "best of 3"},
  "3": "./panel_3.png",
  "4": "./panel_4.png"
}
```

```bash
python scripts/accept_external_panel.py --id scp-173 --manifest ./generated-panels.json --provider imagegen
```

---

## 7. 1コマだけ差し替えて再完成を依頼する

```text
scp-173 の3コマ目だけ差し替えて、漫画を再生成してください。
AGENTS.md を読み、$finalize-scp-comic の手順で進めてください。

画像:
- panel 3: ./panel_3_retry.png

条件:
- 他のpanelは既存の accepted panel を使う
- panel 3だけ accept_external_panel.py で差し替える
- 全言語の完成画像は再生成する
- 最終publication runなので --languages は使わない
```

対応コマンド:

```bash
python scripts/accept_external_panel.py \
  --id scp-173 \
  --panel 3 \
  --source ./panel_3_retry.png \
  --provider imagegen \
  --note "regenerated because previous panel had pseudo-text"

python scripts/run_pipeline.py --id scp-173 --skip-generate
python scripts/publish_check.py scp-173
python scripts/build_review_sheet.py scp-173
```

---

## 8. テキスト修正を依頼する

意味が変わる修正は、15言語すべて更新します。

```text
scp-173 のテキストを修正してください。
AGENTS.md を読み、$revise-comic-text の手順で進めてください。

対象:
- panel: 4
- field: caption
- language scope: semantic-all-languages

修正内容:
- 現在: <任意。分かる範囲で>
- 希望: オチが分かりやすいように短くする
- 理由: 現在のcaptionだと異常性の結論が伝わりにくい

制約:
- 画像は再生成しない
- 意味が変わるので15言語すべて更新する
- 修正後は full-language で再embedする
```

Codexが実行する基本コマンド:

```bash
python scripts/validate_scripts.py comics/done/scp-173.yaml
python scripts/text_revision_check.py scp-173 --expect semantic-all-languages --panel 4 --field caption
python scripts/run_pipeline.py --id scp-173 --skip-generate
python scripts/publish_check.py scp-173
```

`comics/queue/` にある台本なら、`comics/queue/scp-173.yaml` を検証します。

---

## 9. 言語固有の誤字だけ修正する

意味が変わらない誤字・表記ゆれだけなら、特定言語だけ修正してよいです。

```text
$revise-comic-text で scp-173 の日本語タイトルだけ誤字修正してください。
意味は変えません。他言語は変更しないでください。

対象:
- field: title
- language scope: ja-only typo

修正内容:
- 現在: <現在の表記>
- 希望: <修正後の表記>
```

チェックコマンド:

```bash
python scripts/text_revision_check.py scp-173 --expect ja-only --field title
```

ただし、修正後も15言語エントリが欠けていないことは検証します。

---

# imagegen依頼テンプレート

通常は手で組み立てず、`--export-prompts` が生成する `panel_N_imagegen_request.txt` をそのまま使います。

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
cat output/scp-XXX/prompts/panel_1_imagegen_request.txt
```

中身は概ね以下の形です。

```text
Generate a single image for one SCP comic panel.

Hard requirements:
- Use a square 1:1 canvas.
- Produce exactly one standalone illustration for panel N.
- Do not create a comic page, four-panel strip, storyboard, grid, border, frame, or split-screen layout.
- Do not render any text, letters, numbers, captions, signs, labels, sound effects, watermarks, speech bubbles, or thought bubbles.
- Draw one continuous moment only.
- Keep important faces, hands, and props away from the outer edge because the accepted image will be center-cropped/resized to 720x720 if needed.

Use this project prompt exactly as the semantic/art direction:

<project prompt>
```

保存先は任意ですが、管理しやすい推奨先は以下です。

```text
output/scp-XXX/panels_temp/panel_N_imagegen_vM.png
```

`panels_temp/` はgitignore済みです。保存先が違っても、`accept_external_panel.py --source` に渡せば問題ありません。

---

# Pipeline

```text
Codex: $make-scp-comic-script
  ↓
comics/queue/scp-XXX.yaml
  ↓
Python validation
  ↓
Codex: $generate-scp-comic-images
  ↓
python scripts/run_pipeline.py --id scp-XXX --export-prompts [--panel N]
  ↓
output/scp-XXX/prompts/panel_N_imagegen_request.txt
  ↓
ChatGPT image generation (`imagegen`)
  ↓
output/scp-XXX/panels_temp/panel_N_imagegen_vM.png  # raw/debug, gitignored
  ↓
Codex/Python: $finalize-scp-comic
  ↓
python scripts/accept_external_panel.py --id scp-XXX --panel N --source <image>
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

---

# コマンド詳細

## Setup

```bash
pip install -r requirements.txt
python scripts/download_fonts.py
pytest -q
python scripts/validate_scripts.py --all
python scripts/check_forbidden_artifacts.py
```

## Status

```bash
python scripts/comic_status.py scp-XXX
```

台本、prompt、accepted panel、15言語画像、publish checkの状態を一覧します。

## Script validation

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source
python scripts/validate_scripts.py --all
```

YAML構造、15言語caption、character key、caption position、source section policyなどを検証します。画像生成やoutput更新は行いません。新規台本では `--strict-source` を推奨します。

## Prompt export

全コマ分:

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

1コマだけ再生成用:

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts --panel 3
```

## Accept generated panels

1コマ:

```bash
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3_retry.png --provider imagegen --note "regenerated because previous panel had pseudo-text"
```

ディレクトリ一括:

```bash
python scripts/accept_external_panel.py --id scp-XXX --source-dir ./generated/scp-XXX --provider imagegen
```

manifest一括:

```bash
python scripts/accept_external_panel.py --id scp-XXX --manifest ./generated-panels.json --provider imagegen
```

取り込み時に、元画像は `panels_temp/` にコピーされ、accepted panelは `output/scp-XXX/panels/panel_N.png` に720x720で保存されます。`selected.json` にはprompt/scene/provider/元画像サイズ/採用サイズ/正規化方法が残ります。

## Compose, embed, and publish check

全コマを採用した後、または1コマ差し替え後:

```bash
python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX
python scripts/build_review_sheet.py scp-XXX
```

`--skip-generate` は画像生成を行わず、accepted panelsを使って合成・15言語embed・publish gate・index更新を行います。最終publication runでは `--languages ja` のような部分実行を使わないでください。

## Mock

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

mockはproductionと同じpanel pathへplaceholderを書けるため、採用済み未コミット画像がある作品に対して不用意に全コマmockを実行しないでください。1コマ確認では `--panel N` を付けます。

`--variants` は現在mock専用です。実画像の候補生成には使いません。

---

# 出力とコミット対象

通常コミットするもの:

```text
comics/done/scp-XXX.yaml
output/scp-XXX/base.png
output/scp-XXX/thumbnail.png
output/scp-XXX/<lang>.png
output/scp-XXX/meta.json
output/scp-XXX/panels/panel_N.png
output/scp-XXX/panels/selected.json
index.json
state/used.json
```

通常コミットしないもの:

```text
output/scp-XXX/panels_temp/
output/scp-XXX/prompts/
output/scp-XXX/generated-page.png
output/scp-XXX/review-sheet.png
```

CIでも `scripts/check_forbidden_artifacts.py` により、上記の作業用artifactがtrackingされていたら失敗します。

`thumbnail.png` は **`panels/panel_1.png` から直接**作ります。`base.png`、`generated-page.png`、その他ページ合成画像から切り出してはいけません。これにより漫画の余白・枠・caption領域がサムネイルへ混入するのを防ぎます。

`generated-page.png` はproduction pipelineでは生成も参照もしません。外部handoff処理がpreview/debug用に作った場合もdisposable artifactとして扱い、thumbnail/panelの入力にしないでください。

---

# Image sizes

- accepted panel: `config/layout.yaml`（現在 **720x720**）
- thumbnail: 現在 **480x480**
- imagegen/external handoff: 1:1を明示し、accepted targetを720x720として扱う。非正方形で返った場合は単一画像自体を中央crop+resizeし、page画像から切り出さない。

---

# Index API

`index.json` は `schemaVersion` と `generatedAt` を持ちます。各comicには `contentHash` と `assets.*.sha256` も含まれるため、アプリ側でキャッシュバスターや差し替え検知に使えます。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

---

# License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
