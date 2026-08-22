# SCP Reader Comic Generator

SCP記事を題材にした4コマ漫画（コマ数可変）を生成するリポジトリ。台本作成から画像生成まで、
**すべてローカルでClaude Codeが実行する**（自動化・スケジュール実行は無し）。

- **台本**はローカルでClaude Codeと一緒に作成し `comics/queue/` に積む（→ CLAUDE.md）
- **画像生成**はプロバイダ切替式（Gemini / ローカルComfyUI）。
  `config/style.yaml` の `generation.provider` で選んだプロバイダをローカルで実行する
- **セリフ・キャプションは画像に描かせず**、後工程のPythonがSCP Readerアプリの対応15言語分を
  各コマの絵の内側に埋め込む
- 生成物は `output/<id>/` にコミットし、アプリ / SCP紹介bot (X) からraw URLで参照する

## パイプライン

```
comics/queue/scp-XXX.yaml   ← 台本（scene英語 + caption15言語）: ローカルで作成
        │
        ▼  ローカルで python scripts/run_pipeline.py --id scp-XXX を実行
scripts/generate_panels.py  ← コマごとにプロンプトを組み立て、選択中のプロバイダで画像生成（文字なし）
  └ scripts/providers/<name>/   ← 実際のAPI呼び出し（gemini / comfyui）
scripts/compose.py          ← コマを統一サイズで1枚に合成 + ライセンス表記フッター
scripts/embed_text.py       ← 言語別にタイトル・キャプション・吹き出しテキストを埋め込み
scripts/build_index.py      ← index.json 更新
        │
        ▼
output/scp-XXX/base.png     ← テキスト無し版
output/scp-XXX/<lang>.png   ← 言語別（ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant）
output/scp-XXX/meta.json    ← コマ座標・attribution等
index.json                  ← 漫画一覧（アプリ/bot用）
state/used.json             ← 生成済みSCPの記録（重複生成防止。消さないこと）
```

生成済みのSCPと同じIDの台本がキューにあってもスキップされる
（再生成したい場合は台本に `regenerate: true` を書くか、`--id` で明示的に実行する）。

## 画像生成プロバイダ

`config/style.yaml` の `generation.provider` で切り替える。実装は
`scripts/providers/<name>/` に分かれており、各フォルダの `README.md` にセットアップ
手順がある。

| provider | 実行環境 | 特徴 |
|---|---|---|
| `gemini` | クラウドAPI（`GEMINI_API_KEY`が要る） | Nano Banana / Nano Banana Pro。APIキーさえあれば環境を選ばない |
| `comfyui` | ローカルで起動したComfyUIのAPI（`http://127.0.0.1:8188`）を叩く | GPUが要る代わりに無料。モデル・LoRAを差し替えて画風を調整できる |

現在ローカル検証で使っているのは `comfyui`（Qwen-Image 2512 + 2ステップ高速化LoRA +
画風LoRA `QwenImage_blackline`）。プロンプトの組み立て方（`prompt.<provider>` の
style_prompt/composition_rules/no_text_rules）もプロバイダごとに完全に分けて持っており、
モデルによって効く指示の強さ・言い回しが違うことを踏まえて調整してある
（`scripts/generate_panels.py` の `build_prompt()` 参照）。

新しいプロバイダを足す場合は `generate_image(prompt, ref_images, gen_cfg)` を実装して
`scripts/providers/__init__.py` に登録する。

## 設定（すべて後から調整可能）

| ファイル | 役割 |
|---|---|
| `config/style.yaml` | **絵柄の中央定義**（プロバイダ別プロンプト）と生成APIの設定 |
| `config/characters.yaml` | **キャラクターの中央定義**。SCP財団正史（キャノン）の実在職員のみを登録し、複数の漫画で同じ見た目を保つ。参照画像も登録可（オリジナルキャラを創作して登録しないこと。詳細はCLAUDE.md） |
| `config/layout.yaml` | コマサイズ・列数・余白・キャプション/吹き出しの見た目・タイトル/フッター帯 |
| `config/languages.yaml` | 対応言語・フォント割り当て・フォントDL元 |
| `scripts/providers/*/README.md` | 各画像生成プロバイダのセットアップ手順 |

- **8コマにしたい** → 台本のpanelsを8個書くだけ。2列にするなら `layout.yaml` の `strip.columns: 2`
- **絵柄を変えたい** → `style.yaml` の `prompt.<provider>.style_prompt` を書き換え
  （comfyuiの場合は画風LoRAの差し替えが主。台本には絵柄を書かない）
- **キャラを固定したい** → 生成済みのコマからキャラ立ち姿を切り出して `characters/refs/` に置き、
  `characters.yaml` の `reference_images` に登録（以後の生成で参照画像としてAPIに渡される。
  ただしComfyUI側の汎用ワークフローは画像入力に非対応のため、providerによっては無視される）

## セットアップ

```bash
git init まで済み。GitHubへpushしておくと raw.githubusercontent.com 経由で
アプリ/botから画像を参照できる:
gh repo create <name> --public --source . --push
```

`provider: gemini` を使う場合は `GEMINI_API_KEY` 環境変数をローカルにセットしておく
（クラウド上でキーを共有する必要はない。実行のたびに手元の環境から読まれる）。

## ローカルでの動作確認

```bash
pip install -r requirements.txt
python scripts/download_fonts.py

# APIを呼ばずレイアウト・キャプション・多言語埋め込みを確認（プレースホルダー画像）
python scripts/run_pipeline.py --id scp-999 --mock

# 本番同様に生成（config/style.yamlのprovider設定に従う。geminiならGEMINI_API_KEYが要る）
python scripts/run_pipeline.py --id scp-999

# 生成済みコマを使い、合成・埋め込みだけやり直す（レイアウト調整時）
python scripts/run_pipeline.py --id scp-999 --skip-generate --languages ja,en
```

`provider: comfyui` の場合は事前にComfyUIをローカルで起動し、必要なモデル・LoRAを
配置しておくこと（`scripts/providers/comfyui/README.md` 参照）。

### Google AI Studioで手動生成する場合（gemini専用）

APIキーを使わず、[aistudio.google.com](https://aistudio.google.com) のチャットUIで手動生成して
リポジトリに格納することもできる。

```bash
# APIを呼ばず output/scp-999/prompts/ にプロンプト・参照画像・手順書を書き出す
python scripts/run_pipeline.py --id scp-999 --export-prompts
```

`output/scp-999/prompts/README.txt` の手順に従い、`panel_N.txt` の内容をAI Studioに貼り付けて
生成した画像を `output/scp-999/panels/panel_N.png` として保存する。全コマ保存したら
`python scripts/run_pipeline.py --id scp-999 --skip-generate` で合成・多言語埋め込みまで実行できる。

**mock実行の出力（output/）はコミットしないこと**（実生成で上書きされる前提のダミー）。

## アプリ / bot からの参照

```
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/index.json
https://raw.githubusercontent.com/<owner>/<repo>/refs/heads/master/output/<id>/<lang>.png
```

index.jsonは非ASCIIを\uXXXXエスケープして出力する（raw.githubusercontent.comが
charset無しで配信するため。scpjpReaderActionsと同じ方針）。

## ライセンス

- SCP記事は CC BY-SA 3.0。漫画のフッターに出典・著者・ライセンスを自動で表記する
  （`compose.py` の `build_footer_lines`）。この漫画自体も CC BY-SA 3.0 継承
- 注意: 一部SCPの**公式画像**はCCではない（例: SCP-173の彫刻写真）。
  台本のsceneは**記事本文の記述のみ**を根拠に書き、既存画像の模倣はさせない
