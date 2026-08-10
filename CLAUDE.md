# SCP漫画ジェネレーター

SCP記事を題材にした多言語コマ漫画を生成する。生成はGitHub Actions（毎日1本）、
**台本作りはローカルでClaude Codeが行う**。全体像はREADME.md参照。

## 台本作成の手順（「台本を作って」「N本作って」と言われたらこれを実行）

1. 題材のSCPを選ぶ
   - 記事データ: `../scpjp_reader_github_actions/local-data/scp-data.json`（日本語）ほか言語別ディレクトリ
   - `comics/queue/` と `comics/done/` に既にあるIDは避ける
   - ユーザーが指定した場合はそれに従う
2. 記事本文を読み、**4コマのオチのある小話**を構成する（デフォルト4コマ。指示があれば8コマ等も可）
   - ホラーでも軽いコメディ寄りに。グロ・残虐描写は避ける（アプリ/SNS掲載のため）
   - **記事本文の記述のみ**を根拠に描写する。公式添付画像の模倣はしない
     （SCP-173の彫刻写真などCCライセンスでない画像があるため）
3. `comics/queue/scp-XXX.yaml` を書く。既存の台本（`comics/queue/` か `comics/done/` の scp-999.yaml）が書式見本
   - `scene`: 英語で具体的に。構図・表情・小道具まで。**絵柄のことは書かない**（style.yamlが担う）
   - `characters`: 繰り返し登場させるキャラは `config/characters.yaml` に定義してキー名で参照。
     その漫画限りのキャラ・オブジェクトはsceneに直接書く
   - `bubbles`: `position` はプリセット（top / top-left / top-right / bottom / bottom-left /
     bottom-right / center）か正規化座標 `{x,y,w,h}`。`tail` は down / down-left / down-right /
     up / up-left / up-right / left / right
   - `text`: **15言語すべて**書く（ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant）。
     セリフは短く（日本語で20文字前後まで）。翻訳はClaudeが直接書いてよい
   - `attribution`: 記事のURL・著者を記載。著者は記事ページ下部やクレジットモジュールで
     確認できる。不明なら `author` を省略してよい（フッターには出典URLが必ず入る）
4. 検証: `python scripts/run_pipeline.py --id scp-XXX --mock` を実行し、
   吹き出しの位置・あふれ警告（`WARN: text overflow`）を確認。あふれたらセリフを短くする
   - 初回は `pip install -r requirements.txt` と `python scripts/download_fonts.py` が必要
   - **mock実行で作られた output/scp-XXX/ はコミットしない**（`git checkout`等で戻すか削除）

## 実装メモ

- 生成プロンプトの組み立ては `scripts/generate_panels.py` の `build_prompt()`。
  順序: style_prompt → キャラ定義 → scene → 吹き出しスペース確保の指示 → 構図規則 → 文字禁止規則
- 画像には**一切文字を描かせない**。タイトル・セリフ・ライセンスはPython（Pillow）が後から描く
- 言語別フォントに無いグリフ（タイ語フォントのラテン文字等）は `lib/textutil.py` の
  FontSetがNotoSansへ自動フォールバックする
- コマ座標は `output/<id>/meta.json` 経由で `embed_text.py` に渡る。
  `layout.yaml` を変えたら `--skip-generate` で合成・埋め込みだけ再実行できる
- キャラの見た目が漫画間でブレたら: 良いコマから立ち姿を切り出して `characters/refs/` に保存し、
  `config/characters.yaml` の `reference_images` に登録する
