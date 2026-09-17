# SCP Reader Comic Generator

SCP記事を題材に、多言語のコマ漫画を生成してSCP Readerアプリ / 紹介botから参照するリポジトリです。

このREADMEは**人間向けの運用手順**です。Codex向けの常設指示は、短く保った `AGENTS.md` に集約しています。CodexにはREADME全体を毎回読ませず、必要なSkillと対象ファイルだけ読ませる運用を推奨します。

画像生成は ChatGPT 画像生成（`imagegen`）などの外部ツールで行います。このリポジトリは、台本管理・prompt生成・外部生成画像の取り込み・正規化・合成・15言語テキスト埋め込み・publish gateを担当します。

---

## 重要ルール

- 台本は `comics/queue/scp-XXX.yaml` に作る。
- 漫画本文は原則 **Descriptionのみ** から構成する。
- Special Containment Procedures を使うのは例外。使う場合は、Descriptionで構成した1〜3コマ目を受ける自然な「結」になる場合の **4コマ目のみ**。
- 画像は **1コマにつき1枚**。4コマまとめたページ画像を作らない。
- imagegenには **正方形1:1** を依頼する。
- 画像には文字・caption・吹き出し・枠・ページレイアウトを描かせない。
- 人間は基本的に `panel_N_imagegen_request.txt` を確認しない。prompt exportは内部handoffで、通常はそのままimagegenへ渡す。
- 1コマだけ失敗した場合は、そのコマだけ再生成・差し替えする。全コマを再生成しない。
- 意味が変わるテキスト修正は、必ず15言語すべて更新する。

---

## Token-saving運用

Codexのトークン消費を抑えるため、依頼文では**読む範囲**を明示してください。

基本方針:

- README全体は読ませない。READMEは人間用。
- `AGENTS.md` は短い常設ルールとして読む。
- 作業に対応するSkillだけ読む。複合依頼なら必要なSkillだけ読む。
- 対象SCPのYAMLと、対象SCPの `output/<id>/` 配下だけ読む。
- 他のSCP YAML、他のoutput、リポジトリ全体検索は避ける。
- まず `comic_status.py --json` で状態確認する。
- Pythonコマンドは `--quiet` / `--json` を優先する。
- `validate_scripts.py --all` はCI・全体変更・merge前確認だけに使う。

Codex依頼テンプレ:

```text
トークン節約モードで進めてください。

読む範囲は以下に限定してください。
- AGENTS.md
- .agents/skills/<使うSkill>/SKILL.md
- comics/queue/scp-XXX.yaml または comics/done/scp-XXX.yaml
- 必要な output/scp-XXX/ 配下の meta.json / selected.json / prompts/manifest.json

README全体、他のSCP YAML、他のoutput、リポジトリ全体検索は読まないでください。
まず python scripts/comic_status.py scp-XXX --json を実行し、必要な次工程だけ判断してください。
コマンド出力は可能な限り --quiet / --json を使ってください。
```

---

## User-facing Codex Skills

普段の運用は、この4つのSkillだけを使います。

| 作業 | Skill | 内容 |
|---|---|---|
| 台本作成 | `$make-scp-comic-script` | live記事確認 → YAML作成/修正 → internal review → validation |
| 画像生成 | `$generate-scp-comic-images` | imagegen request export → panelごとの `imagegen` 生成。1コマ再生成も担当 |
| 生成済み画像取り込み漫画完成 | `$finalize-scp-comic` | 画像取り込み → 720x720正規化 → 15言語embed → publish check |
| テキスト修正 | `$revise-comic-text` | caption/title/addendum等を修正。意味変更時は15言語すべて更新 |

低レベルSkill（write/review/prepare/refine/handoff）は、上記のユーザー向けSkillに統合済みです。

---

## 最短フロー

新しいSCP漫画を1本作る場合:

```text
1. Codexに台本作成〜全コマ画像生成まで依頼
   $make-scp-comic-script → $generate-scp-comic-images

2. 生成されたraw画像を確認し、採用する画像パスを決める

3. Codexに生成済み画像の取り込み・漫画完成を依頼
   $finalize-scp-comic
```

通常、`panel_N_imagegen_request.txt` は人間が確認しません。Codex / imagegenへのhandoff用に自動生成される中間ファイルです。promptだけ確認したい場合は、明示的に「画像生成はせずpromptだけ出して」と依頼してください。

ローカルコマンド中心で見ると:

```bash
python scripts/comic_status.py scp-XXX --json
python scripts/create_script_stub.py scp-XXX --quiet
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source --quiet
python scripts/run_pipeline.py --id scp-XXX --export-prompts

# imagegenで各panel画像を作成後
python scripts/accept_external_panel.py --id scp-XXX --panel 1 --source /path/to/panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 2 --source /path/to/panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 4 --source /path/to/panel_4.png --provider imagegen

python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX --json
```

途中状態が分からなくなったら、まずこれだけ実行します。

```bash
python scripts/comic_status.py scp-XXX --json
```

---

# 依頼テンプレート集

## 1. 台本作成だけ依頼する

画像生成まで進めたくない場合だけ、このテンプレートを使います。

```text
scp-173 の漫画台本を作ってください。
トークン節約モードで進めてください。
AGENTS.md と $make-scp-comic-script だけ読み、README全体や他のSCP YAMLは読まないでください。

条件:
- live記事を確認する
- Description優先で4コマにする
- Special Containment Proceduresを使う場合は4コマ目のみ
- まず python scripts/create_script_stub.py scp-173 --quiet でYAML骨組みを作る
- source provenance を各panelに入れる
- 15言語captionを作る
- internal reviewを行う
- python scripts/validate_scripts.py comics/queue/scp-173.yaml --strict-source --quiet を実行する

画像生成はまだしないでください。
```

成果物:

```text
comics/queue/scp-173.yaml
```

## 2. 台本作成から全コマimagegen画像生成まで依頼する

新規作成時の標準テンプレートです。**台本作成、prompt export、全コマimagegen生成を1つの依頼で進めます。** 人間は通常、imagegen用promptを確認しません。

```text
scp-173 の漫画を、台本作成から全コマ画像生成まで進めてください。
トークン節約モードで進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/make-scp-comic-script/SKILL.md
- .agents/skills/generate-scp-comic-images/SKILL.md
- comics/queue/scp-173.yaml または comics/done/scp-173.yaml（存在する場合）
- 必要な output/scp-173/ 配下のみ

README全体、他のSCP YAML、他のoutput、リポジトリ全体検索は読まないでください。

やること:
1. python scripts/comic_status.py scp-173 --json
2. $make-scp-comic-script で台本を作る
3. python scripts/validate_scripts.py comics/queue/scp-173.yaml --strict-source --quiet
4. python scripts/run_pipeline.py --id scp-173 --export-prompts
5. output/scp-173/prompts/panel_N_imagegen_request.txt を人間確認なしでimagegenに渡す
6. imagegenで1コマにつき1枚の正方形画像を生成する
7. 生成したraw画像パスを報告する

画像の取り込みと漫画完成はまだしないでください。
```

成果物:

```text
comics/queue/scp-173.yaml
output/scp-173/prompts/panel_1_imagegen_request.txt
output/scp-173/prompts/panel_2_imagegen_request.txt
output/scp-173/prompts/panel_3_imagegen_request.txt
output/scp-173/prompts/panel_4_imagegen_request.txt
output/scp-173/prompts/manifest.json
output/scp-173/panels_temp/<imagegen raw images>
```

`panel_N_imagegen_request.txt` は、画像生成の再現性・デバッグ用にも残しますが、通常はレビュー待ちにしません。

## 3. 既存台本から全コマ画像生成だけ依頼する

台本が既にある場合のテンプレートです。

```text
既存台本 scp-173 の全コマ画像を生成してください。
トークン節約モードで、$generate-scp-comic-images の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/generate-scp-comic-images/SKILL.md
- comics/queue/scp-173.yaml または comics/done/scp-173.yaml
- output/scp-173/prompts/manifest.json（存在する場合）

条件:
- ChatGPT画像生成（imagegen）を使う
- output/scp-173/prompts/panel_N_imagegen_request.txt を人間確認なしで使う
- 1コマにつき1枚の正方形画像を生成する
- 漫画ページ、複数コマ、grid、frame、border、文字、caption、吹き出しは生成しない
- 生成したraw画像パスを報告する

完成処理はまだしないでください。
```

Codexが実行する基本コマンド:

```bash
python scripts/comic_status.py scp-173 --json
python scripts/validate_scripts.py comics/queue/scp-173.yaml --quiet
python scripts/run_pipeline.py --id scp-173 --export-prompts
```

## 4. promptだけ出力する（例外運用）

人間がpromptを確認したい場合だけ、明示的にこの依頼をします。

```text
scp-173 のimagegen用promptだけ出力してください。
画像生成はしないでください。
$generate-scp-comic-images のprompt exportまでで止めてください。
```

対応コマンド:

```bash
python scripts/run_pipeline.py --id scp-173 --export-prompts
```

## 5. 1コマだけ画像再生成を依頼する

1コマだけ失敗した場合は、必ずそのコマだけを対象にします。

```text
scp-173 の3コマ目だけ再生成してください。
トークン節約モードで、$generate-scp-comic-images の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/generate-scp-comic-images/SKILL.md
- comics/queue/scp-173.yaml または comics/done/scp-173.yaml
- output/scp-173/panels/selected.json
- output/scp-173/prompts/manifest.json

対象:
- panel: 3

理由:
- 既存の3コマ目に文字っぽいものが写っている
- 他のコマはそのまま使う

やること:
- python scripts/comic_status.py scp-173 --json を実行する
- 必要なら panel 3 の scene だけ修正する
- python scripts/validate_scripts.py comics/queue/scp-173.yaml --quiet を実行する
- python scripts/run_pipeline.py --id scp-173 --export-prompts --panel 3 を実行する
- output/scp-173/prompts/panel_3_imagegen_request.txt を人間確認なしでimagegenに渡す
- imagegenでpanel 3だけ生成する
- 生成したraw画像パスを報告する

完成処理はまだしないでください。
```

対応コマンド:

```bash
python scripts/run_pipeline.py --id scp-173 --export-prompts --panel 3
```

## 6. 生成済み画像を取り込んで漫画完成を依頼する

```text
scp-173 の生成済み画像を取り込んで漫画を完成させてください。
トークン節約モードで、$finalize-scp-comic の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/finalize-scp-comic/SKILL.md
- comics/queue/scp-173.yaml または comics/done/scp-173.yaml
- output/scp-173/panels/selected.json
- output/scp-173/meta.json

画像:
- panel 1: ./panel_1.png
- panel 2: ./panel_2.png
- panel 3: ./panel_3.png
- panel 4: ./panel_4.png

やること:
- python scripts/comic_status.py scp-173 --json を実行する
- scripts/accept_external_panel.py で各panelを取り込む
- python scripts/run_pipeline.py --id scp-173 --skip-generate を実行する
- python scripts/publish_check.py scp-173 --json を実行する
```

対応コマンド:

```bash
python scripts/accept_external_panel.py --id scp-173 --panel 1 --source ./panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 2 --source ./panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 3 --source ./panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-173 --panel 4 --source ./panel_4.png --provider imagegen
python scripts/run_pipeline.py --id scp-173 --skip-generate
python scripts/publish_check.py scp-173 --json
```

画像ファイルが `panel_1.png`、`panel_2.png`、... という名前で同じディレクトリにある場合は、一括取り込みできます。

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

## 7. 1コマだけ差し替えて再完成を依頼する

```text
scp-173 の3コマ目だけ差し替えて、漫画を再生成してください。
トークン節約モードで、$finalize-scp-comic の手順で進めてください。

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
python scripts/publish_check.py scp-173 --json
```

## 8. テキスト修正を依頼する

意味が変わる修正は、15言語すべて更新します。

```text
scp-173 のテキストを修正してください。
トークン節約モードで、$revise-comic-text の手順で進めてください。

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

基本コマンド:

```bash
python scripts/validate_scripts.py comics/done/scp-173.yaml --quiet
python scripts/text_revision_check.py scp-173 --expect semantic-all-languages --panel 4 --field caption
python scripts/run_pipeline.py --id scp-173 --skip-generate
python scripts/publish_check.py scp-173 --json
```

言語固有の誤字だけなら、特定言語だけ修正してよいです。

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

---

# imagegen依頼ファイル

`run_pipeline.py --export-prompts` を実行すると、各panelについて2種類のファイルが出ます。

```text
output/scp-XXX/prompts/panel_N.txt
output/scp-XXX/prompts/panel_N_imagegen_request.txt
```

通常使うのは **`panel_N_imagegen_request.txt`** です。以下の要件がすでに含まれているため、人間がREADMEのテンプレを貼り合わせる必要はありません。

```text
- square 1:1 canvas
- exactly one standalone illustration
- no comic page / strip / storyboard / grid / border / frame / split-screen
- no text / captions / signs / labels / watermarks / speech bubbles
- one continuous moment only
```

`panel_N.txt` は低レベルのproject promptです。デバッグ以外では直接使わない想定です。

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
python scripts/comic_status.py scp-XXX --json
python scripts/comic_status.py scp-XXX --quiet
```

## Script stub

```bash
python scripts/create_script_stub.py scp-XXX --quiet
python scripts/create_script_stub.py scp-XXX --json
```

## Script validation

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source --quiet
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --json
python scripts/validate_scripts.py --all
```

`--all` はCI・全体変更・merge前確認向けです。通常作業では対象YAMLだけを検証します。

## Prompt / imagegen request export

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
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3.png --provider imagegen
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
python scripts/publish_check.py scp-XXX --json
```

最終publication runでは `--languages ja` のような部分実行を使わないでください。

## Review sheet

```bash
python scripts/build_review_sheet.py scp-XXX
```

`output/scp-XXX/review-sheet.png` は確認用です。コミットしません。

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

これらは `.gitignore` とCIの `check_forbidden_artifacts.py` で検出します。

`thumbnail.png` は **`panels/panel_1.png` から直接**作ります。`base.png`、`generated-page.png`、その他ページ合成画像から切り出してはいけません。

---

# Image sizes

- accepted panel: `config/layout.yaml`（現在 **720x720**）
- thumbnail: 現在 **480x480**
- imagegen/external handoff: 1:1を明示し、accepted targetを720x720として扱う。非正方形で返った場合は単一画像自体を中央crop+resizeし、page画像から切り出さない。

---

# Index API

`index.json` は `schemaVersion`、`generatedAt`、各comicの `contentHash`、asset-level SHA-256 を持ちます。アプリ側は将来のschema変更や画像差し替え検知に使えます。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

---

# License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
