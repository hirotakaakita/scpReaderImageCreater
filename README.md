# SCP Reader Comic Generator

SCP記事を題材にした多言語コマ漫画を生成するリポジトリです。台本作成・レビュー・コード変更は **Codex** を前提にし、画像生成はローカルのComfyUI、文字合成と公開判定はPythonで行います。

エージェント向けの常設ルールは `AGENTS.md`、モデル非依存の漫画仕様は `docs/comic-spec.md`、Codexの作業手順は `.agents/skills/` を参照してください。

## パイプライン

```text
live SCP article
      ↓
Codex: write-scp-script
      ↓
comics/queue/scp-XXX.yaml
      ↓
Codex: review-scp-script
      ↓
python scripts/validate_scripts.py ...
      ↓
python scripts/run_pipeline.py --id scp-XXX --variants N
      ↓
ComfyUIで候補生成 → 人が採用コマを選択
      ↓
python scripts/run_pipeline.py --id scp-XXX --skip-generate
      ↓
compose.py → embed_text.py → publish-complete判定 → build_index.py
```

LLMに任せるのは、原文読解・台本構成・レビュー・scene改善などの曖昧な判断です。YAML構造、参照キャラクター、対応言語、公開可能状態など機械判定できる条件はPythonで検証します。

## 出力

```text
output/scp-XXX/base.png       テキスト無し合成版
output/scp-XXX/<lang>.png     言語別完成画像
output/scp-XXX/thumbnail.png  一覧用サムネイル
output/scp-XXX/meta.json      レイアウト・attribution・公開状態
index.json                    アプリ / bot 用一覧
state/used.json               重複生成防止台帳（移行完了まで削除禁止）
```

対応言語は `config/languages.yaml` が唯一の定義元です。

## Codex Skills

- `$write-scp-script` — live記事から台本を作成・修正
- `$review-scp-script` — writerとは別の視点で原文整合性・起承転結をレビュー
- `$prepare-scp-comic` — 台本→レビュー→mock→prompt exportまで準備
- `$refine-panel` — 生成済み1コマの候補を評価しsceneを反復改善

WriterとReviewerはどちらもCodexですが、役割を分離します。Reviewerはまず指摘のみを返し、原文を確認した上で妥当なものだけ修正します。

## セットアップ

```bash
pip install -r requirements.txt
python scripts/download_fonts.py
```

画像生成を行う場合はComfyUIをローカルで起動し、`scripts/providers/comfyui/README.md` のモデル・LoRA・workflow設定を用意してください。現在の画像providerは `comfyui` です。provider実装は `scripts/providers/<name>/` に分離されています。

## 台本検証

```bash
# 1本
python scripts/validate_scripts.py comics/queue/scp-XXX.yaml

# queue / done 全件
python scripts/validate_scripts.py --all

# unit tests
pytest -q
```

台本ロード時にも同じ基本validationが走ります。主に次を検証します。

- `id` / `panels` / `scene` / `caption`
- production言語のcaption欠落
- 未定義character key
- caption/bubble preset名
- ファイル名とscript IDの不整合

## mock

ComfyUIを呼ばず、レイアウト・文字あふれ等を確認できます。

```bash
python scripts/run_pipeline.py --id scp-XXX --mock
```

mockは本番と同じ `output/<id>/` 配下へプレースホルダーを書きます。未コミットの採用済みpanelがある状態で不用意に全コマmockを実行しないでください。1コマ確認なら必ず `--panel N` を付けます。mock成果物は本番成果物としてコミットしません。

## 画像生成

```bash
python scripts/run_pipeline.py --id scp-XXX --variants 4
```

候補は `output/scp-XXX/panels_temp/panel_N_vM.png` に追加され、採用済み `panels/panel_N.png` は上書きしません。候補を目視して採用画像を `panels/panel_N.png` に置いた後、次を実行します。

```bash
python scripts/run_pipeline.py --id scp-XXX --skip-generate
```

ComfyUIの複数漫画生成を並列実行しないでください。キュー詰まりとGPU/RAM逼迫を避けるため、複数IDも直列処理します。

1コマだけ候補を追加する場合:

```bash
python scripts/run_pipeline.py --id scp-XXX --panel 3 --variants 4
```

## 部分言語レンダリングと公開状態

```bash
python scripts/run_pipeline.py --id scp-XXX --skip-generate --languages ja,en
```

これは確認・部分再生成用です。**部分言語実行だけではpublish-completeになりません。** `compose.py` は再合成時に公開状態を `complete: false` へ戻し、全production言語を正常に埋め込んだ実行だけが `complete: true` にできます。`run_pipeline.py` は明示的な `True` の場合だけqueue→done移動と `state/used.json` 記録を行います。

## prompt export

ComfyUI APIを呼ばず最終promptを書き出せます。

```bash
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

`output/scp-XXX/prompts/` に各コマのpromptが生成されます。

## 設定

| ファイル | 役割 |
|---|---|
| `config/style.yaml` | provider・モデル・生成設定・provider別prompt |
| `config/characters.yaml` | 複数漫画で使うキャラクター定義 |
| `config/layout.yaml` | コマ・caption・header/footer等のレイアウト |
| `config/languages.yaml` | production言語・フォント・AI利用告知 |
| `docs/comic-spec.md` | 原文利用・台本・キャラ・公開品質の仕様 |

絵柄は `style.yaml` 側で管理し、各台本の `scene` には書きません。記事固有人物は台本の `local_characters` に置きます。

## アプリ / bot からの参照

公開後はraw GitHub URLから `index.json` と画像を参照できます。

```text
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

画像数が増えてリポジトリサイズが問題になった場合は、生成画像をObject Storage/CDNへ分離する予定です。コード・台本・meta/indexをGitHub側に残す構成を想定しています。

## ライセンス

SCP記事はCC BY-SA 3.0です。漫画のフッターに出典・著者・ライセンスを自動表記し、この漫画もCC BY-SA 3.0を継承します。一部記事の公式添付画像は同じライセンスではない場合があるため、画像を模倣せず記事本文の記述をvisual sourceとして使用します。
