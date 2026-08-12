# SCP Reader Comic Generator

SCP記事を題材にした4コマ漫画（コマ数可変）を自動生成するリポジトリ。

- **台本**はローカルでClaude Codeと一緒に作成し `comics/queue/` に積む（→ CLAUDE.md）
- **画像生成**はGitHub Actionsが毎日1本、Nano Banana Pro (Gemini) で実行
- **セリフは画像に描かせず**、後工程のPythonがSCP Readerアプリの対応15言語分を吹き出しごと埋め込む
- 生成物は `output/<id>/` にコミットされ、アプリ / SCP紹介bot (X) からraw URLで参照する

## パイプライン

```
comics/queue/scp-XXX.yaml   ← 台本（scene英語 + セリフ15言語）: ローカルで作成
        │
        ▼  GitHub Actions（毎日 6:00 JST / 手動実行可）
scripts/generate_panels.py  ← コマごとにNano Banana Proで画像生成（文字なし）
scripts/compose.py          ← コマを統一サイズで1枚に合成 + ライセンス表記フッター
scripts/embed_text.py       ← 言語別にタイトル・吹き出しテキストを埋め込み
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
（再生成したい場合は台本に `regenerate: true` を書くか、手動実行で台本IDを指定する）。

## 設定（すべて後から調整可能）

| ファイル | 役割 |
|---|---|
| `config/style.yaml` | **絵柄の中央定義**（全漫画共通のプロンプト）と生成APIの設定（provider/model切り替え含む） |
| `config/characters.yaml` | **キャラクターの中央定義**。複数の漫画で同じ見た目を保つ。参照画像も登録可 |
| `config/layout.yaml` | コマサイズ・列数・余白・吹き出しの見た目・タイトル/フッター帯 |
| `config/languages.yaml` | 対応言語・フォント割り当て・フォントDL元 |

- **8コマにしたい** → 台本のpanelsを8個書くだけ。2列にするなら `layout.yaml` の `strip.columns: 2`
- **絵柄を変えたい** → `style.yaml` の `style_prompt` を書き換え（台本には絵柄を書かない）
- **キャラを固定したい** → 生成済みのコマからキャラ立ち姿を切り出して `characters/refs/` に置き、
  `characters.yaml` の `reference_images` に登録（以後の生成で参照画像としてAPIに渡される）

## セットアップ

画像生成モデル（Gemini / Nano Banana）は無料枠が無い（quota 0）ため、
どちらかの課金設定が必須。`config/style.yaml` の `generation.provider` で選ぶ。

```bash
# provider: gemini の場合（Google AI Studio直接）
# → AI StudioでAPIキーのプロジェクトにGCPの請求先アカウントを紐付けてから:
gh secret set GEMINI_API_KEY --repo <owner>/<repo>

# provider: openrouter の場合（OpenRouter経由。既定）
# → openrouter.ai でアカウント作成しクレジットを入金してから:
gh secret set OPENROUTER_API_KEY --repo <owner>/<repo>
```

OpenRouterはGCPの請求先アカウント紐付けが不要で、クレジットカードでの入金だけで
使い始められる（同じGeminiモデルをOpenRouter経由で呼ぶだけなので画質・機能差は無い）。
料金はどちらの経路でもほぼ同額（Gemini API従量課金相当）。

Actionsは毎日 6:00 JST に `comics/queue/` の先頭（ファイル名昇順）を1本処理し、
台本を `comics/done/` に移動してコミットする。キューが空の日は何もしない。
手動実行（Actionsタブ）では台本IDや本数を指定できる。

## ローカルでの動作確認

```bash
pip install -r requirements.txt
python scripts/download_fonts.py

# APIを呼ばずレイアウト・吹き出し・多言語埋め込みを確認（プレースホルダー画像）
python scripts/run_pipeline.py --id scp-999 --mock

# 本番同様に生成（要 GEMINI_API_KEY）
set GEMINI_API_KEY=... && python scripts/run_pipeline.py --id scp-999

# 生成済みコマを使い、合成・埋め込みだけやり直す（レイアウト調整時）
python scripts/run_pipeline.py --id scp-999 --skip-generate --languages ja,en
```

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
