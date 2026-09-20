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
- 1コマだけ失敗した場合は、そのコマだけ再生成・差し替えする。全コマを再生成しない。
- 意味が変わるテキスト修正は、必ず15言語すべて更新する。

---

## Token-saving運用

Codexのトークン消費を抑えるため、依頼文では**読む範囲**を明示してください。

基本方針:

- README全体は読ませない。READMEは人間用。
- `AGENTS.md` は短い常設ルールとして読む。
- 作業に対応するSkillを1つだけ読む。
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

1コマ再生成時の例:

```text
トークン節約モードで、scp-008 の3コマ目だけ再生成してください。
$generate-scp-comic-images の手順で進めてください。
他のコマは変更しないでください。
```

テキスト修正時の例:

```text
トークン節約モードで、scp-008 の4コマ目captionだけ修正してください。
$revise-comic-text の手順で進めてください。
意味が変わるので15言語すべて更新してください。
他のpanel/scene/imageは変更しないでください。
```

---

## User-facing Codex Skills

普段の運用は、この4つのSkillだけを使います。

| 作業 | Skill | 内容 |
|---|---|---|
| 台本作成 | `$make-scp-comic-script` | live記事確認 → YAML作成/修正 → internal review → validation |
| 画像生成 | `$generate-scp-comic-images` | prompt export → panelごとの `imagegen` 依頼/生成。1コマ再生成も担当 |
| 生成済み画像取り込み漫画完成 | `$finalize-scp-comic` | 画像取り込み → 720x720正規化 → 15言語embed → publish check |
| テキスト修正 | `$revise-comic-text` | caption/title/addendum等を修正。意味変更時は15言語すべて更新 |

低レベルSkill（write/review/prepare/refine/handoff）は、上記のユーザー向けSkillに統合済みです。

---

## 最短フロー

新しいSCP漫画を1本作る場合:

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

```text
scp-008 の漫画台本を作ってください。
トークン節約モードで進めてください。
AGENTS.md と $make-scp-comic-script だけ読み、README全体や他のSCP YAMLは読まないでください。

条件:
- live記事を確認する
- Description優先で4コマにする
- Special Containment Proceduresを使う場合は4コマ目のみ
- まず python scripts/create_script_stub.py scp-008 --quiet でYAML骨組みを作る
- source provenance を各panelに入れる
- 15言語captionを作る
- internal reviewを行う
- python scripts/validate_scripts.py comics/queue/scp-008.yaml --strict-source --quiet を実行する

画像生成はまだしないでください。
```

成果物:

```text
comics/queue/scp-008.yaml
```

## 2. 台本作成から全コマ画像生成まで一括で依頼する

```text
scp-008 の漫画台本を作成し、imagegenで全4コマの画像生成まで続けて実施してください。
トークン節約モードで進めてください。
読む範囲は AGENTS.md、$make-scp-comic-script、$generate-scp-comic-images、対象YAML、対象のlive記事・公式タイトル情報、両Skillsが必要とする設定・画風参照、output/scp-008/ の必要ファイルに絞ってください。
README全体や他のSCP YAMLは読まないでください。

1. python scripts/comic_status.py scp-008 --json
2. $make-scp-comic-script で台本作成（既存なら確認・必要な修正のみ）
   - 新規なら python scripts/create_script_stub.py scp-008 --quiet で骨組みを作る
   - live記事のDescription優先で4コマにし、収容手順は必要な場合の4コマ目のみ
   - 15言語の公式タイトル・captionと各panelのsource provenanceを入れ、internal reviewを行う
3. python scripts/validate_scripts.py comics/queue/scp-008.yaml --strict-source --quiet（doneにある場合はそのパス）
4. $generate-scp-comic-images で python scripts/run_pipeline.py --id scp-008 --export-prompts を実行
5. output/scp-008/prompts/panel_N_imagegen_request.txt を使い、ChatGPT画像生成（imagegen）で各コマ1枚ずつ生成
6. 生成画像を確認し、必要なコマだけ再生成して、各panelのraw画像パスを報告

条件:
- 1コマにつき1枚の正方形画像を生成する
- 漫画ページ、複数コマ、grid、frame、border、文字、caption、吹き出しは生成しない
- imagegen用promptは人間が確認しないため、台本完成やprompt exportで停止せず、確認待ちなしで全コマ画像生成まで進める
- prompt全文の提示は不要。中間ファイルとして保存し、そのままimagegenに渡す

画像の取り込みと漫画完成はまだしないでください。
```

成果物:

```text
comics/queue/scp-008.yaml（既存のdone台本を使った場合はそのパス）
output/scp-008/prompts/panel_N_imagegen_request.txt（N=1〜4、中間ファイル）
output/scp-008/prompts/manifest.json
各panelの生成済みraw画像（実際の保存先を報告）
```

画像だけを生成し直す場合は、`$generate-scp-comic-images`で対象SCPの全コマ生成を依頼できます。

## 3. 1コマだけ画像再生成を依頼する

1コマだけ失敗した場合は、必ずそのコマだけを対象にします。

```text
scp-008 の3コマ目だけ再生成してください。
トークン節約モードで、$generate-scp-comic-images の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/generate-scp-comic-images/SKILL.md
- comics/queue/scp-008.yaml または comics/done/scp-008.yaml
- output/scp-008/panels/selected.json
- output/scp-008/prompts/manifest.json

対象:
- panel: 3

理由:
- 既存の3コマ目に文字っぽいものが写っている
- 他のコマはそのまま使う

やること:
- python scripts/comic_status.py scp-008 --json を実行する
- 必要なら panel 3 の scene だけ修正する
- python scripts/validate_scripts.py comics/queue/scp-008.yaml --quiet を実行する
- python scripts/run_pipeline.py --id scp-008 --export-prompts --panel 3 を実行する
- output/scp-008/prompts/panel_3_imagegen_request.txt を使って imagegen でpanel 3だけ生成する
- 生成したraw画像パスを報告する

完成処理はまだしないでください。
```

対応コマンド:

```bash
python scripts/run_pipeline.py --id scp-008 --export-prompts --panel 3
```

## 4. 生成済み画像を取り込んで漫画完成を依頼する

```text
scp-008 の生成済み画像を取り込んで漫画を完成させてください。
トークン節約モードで、$finalize-scp-comic の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/finalize-scp-comic/SKILL.md
- comics/queue/scp-008.yaml または comics/done/scp-008.yaml
- output/scp-008/panels/selected.json
- output/scp-008/meta.json

画像:
- panel 1: ./panel_1.png
- panel 2: ./panel_2.png
- panel 3: ./panel_3.png
- panel 4: ./panel_4.png

やること:
- python scripts/comic_status.py scp-008 --json を実行する
- scripts/accept_external_panel.py で各panelを取り込む
- python scripts/run_pipeline.py --id scp-008 --skip-generate を実行する
- python scripts/publish_check.py scp-008 --json を実行する
```

対応コマンド:

```bash
python scripts/accept_external_panel.py --id scp-008 --panel 1 --source ./panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-008 --panel 2 --source ./panel_2.png --provider imagegen
python scripts/accept_external_panel.py --id scp-008 --panel 3 --source ./panel_3.png --provider imagegen
python scripts/accept_external_panel.py --id scp-008 --panel 4 --source ./panel_4.png --provider imagegen
python scripts/run_pipeline.py --id scp-008 --skip-generate
python scripts/publish_check.py scp-008 --json
```

## 5. 1コマだけ差し替えて再完成を依頼する

```text
scp-008 の3コマ目だけ差し替えて、漫画を再生成してください。
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
  --id scp-008 \
  --panel 3 \
  --source ./panel_3_retry.png \
  --provider imagegen \
  --note "regenerated because previous panel had pseudo-text"

python scripts/run_pipeline.py --id scp-008 --skip-generate
python scripts/publish_check.py scp-008 --json
```

## 6. テキスト修正を依頼する

意味が変わる修正は、15言語すべて更新します。

```text
scp-008 のテキストを修正してください。
トークン節約モードで、$revise-comic-text の手順で進めてください。

読む範囲:
- AGENTS.md
- .agents/skills/revise-comic-text/SKILL.md
- comics/done/scp-008.yaml または comics/queue/scp-008.yaml
- output/scp-008/meta.json

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
python scripts/comic_status.py scp-008 --json
python scripts/validate_scripts.py comics/done/scp-008.yaml --quiet
python scripts/run_pipeline.py --id scp-008 --skip-generate
python scripts/publish_check.py scp-008 --json
```

言語固有の誤字だけなら:

```text
$revise-comic-text で scp-008 の日本語タイトルだけ誤字修正してください。
意味は変えません。他言語は変更しないでください。

対象:
- field: title
- language scope: ja-only typo

修正内容:
- 現在: <現在の表記>
- 希望: <修正後の表記>
```

---

# コマンド詳細

## Setup

```bash
pip install -r requirements.txt
python scripts/download_fonts.py
pytest -q
python scripts/validate_scripts.py --all
```

## Status first

```bash
python scripts/comic_status.py scp-XXX --json
python scripts/comic_status.py scp-XXX --quiet
```

Codex作業では、最初に `--json` で状態確認します。人間がざっくり見るだけなら `--quiet` が便利です。

## Script stub

```bash
python scripts/create_script_stub.py scp-XXX --quiet
python scripts/create_script_stub.py scp-XXX --json
python scripts/create_script_stub.py scp-XXX --panels 4 --force
```

15言語caption、title、source provenanceの骨組みをPythonで作ります。Codexには空欄を埋めさせるだけにします。

## Script validation

```bash
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --quiet
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml --strict-source --json
python scripts/validate_scripts.py --all
```

`--all` はCI・全体変更・merge前確認用です。日常作業では対象YAMLだけ検証します。

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

```bash
python scripts/accept_external_panel.py --id scp-XXX --panel 1 --source /path/to/panel_1.png --provider imagegen
python scripts/accept_external_panel.py --id scp-XXX --panel 3 --source /path/to/panel_3_retry.png --provider imagegen --note "one-panel rerun"
```

取り込み時に、元画像は `panels_temp/` にコピーされ、accepted panelは `output/scp-XXX/panels/panel_N.png` に720x720で保存されます。

## Compose, embed, and publish check

```bash
python scripts/run_pipeline.py --id scp-XXX --skip-generate
python scripts/publish_check.py scp-XXX --json
python scripts/publish_check.py scp-XXX --quiet
```

最終publication runでは `--languages ja` のような部分実行を使わないでください。

---

# imagegen依頼ファイル

`--export-prompts` 後に生成される以下をChatGPT画像生成へ貼ります。

```text
output/scp-XXX/prompts/panel_N_imagegen_request.txt
```

このファイルには、以下がすでに含まれています。

- square 1:1
- one standalone illustration
- no page/grid/strip/frame/border
- no text/caption/speech bubble/watermark
- project prompt

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

`thumbnail.png` は `panels/panel_1.png` から直接作ります。`base.png`、`generated-page.png`、その他ページ合成画像から切り出してはいけません。

---

# Index API

`index.json` は `schemaVersion` と `generatedAt` を持ちます。アプリ側は将来のschema変更に備えて `schemaVersion` を確認できる構造にしてください。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

---

# License

SCP記事はCC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動表記し、本漫画もCC BY-SA 3.0を継承します。一部の公式添付画像はCCではないため、画像そのものを模倣せず記事本文の記述を視覚化します。
