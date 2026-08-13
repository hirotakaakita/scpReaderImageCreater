# SCP漫画ジェネレーター

SCP記事を題材にした多言語コマ漫画を生成する。生成はGitHub Actions（毎日1本）、
**台本作りはローカルでClaude Codeが行う**。全体像はREADME.md参照。

## 台本作成の手順（「台本を作って」「N本作って」と言われたらこれを実行）

1. 題材のSCPを選ぶ
   - 記事データ: `../scpjp_reader_github_actions/local-data/scp-data.json`（日本語）ほか言語別ディレクトリ
   - **`state/used.json`（生成済みSCPの記録）にあるIDと、`comics/queue/` に積まれているIDは避ける**。
     used.jsonはActionsが生成成功時に自動更新する。**消すと重複生成の恐れがあるので消さない**
   - パイプラインも二重防御として、used.jsonにあるIDの台本をキューから
     スキップする（意図的に再生成したい場合は台本に `regenerate: true` を書くか `--id` で実行）
   - ユーザーが指定した場合はそれに従う
2. 記事本文を読み、**4コマのオチのある小話**を構成する（デフォルト4コマ。指示があれば8コマ等も可）
   - ホラーでも軽いコメディ寄りに。グロ・残虐描写は避ける（アプリ/SNS掲載のため）
   - **記事本文の記述のみ**を根拠に描写する。公式添付画像の模倣はしない
     （SCP-173の彫刻写真などCCライセンスでない画像があるため）
3. `comics/queue/scp-XXX.yaml` を書く。既存の台本（`comics/queue/` か `comics/done/` の scp-999.yaml）が書式見本
   - `scene`: 英語で具体的に。構図・表情・小道具まで。**絵柄のことは書かない**（style.yamlが担う）
     - **同じ漫画の4コマで同じショット（画角・アングル・構図）を繰り返さない**。各コマの冒頭で
       ショット種別を明示する（例: "Wide shot, full body, showing the whole room..." /
       "Medium shot, waist-up..." / "Close-up on her face..." / "Low angle looking up at..."）。
       起承転結に合わせて 遠景（状況説明）→ 中景（動作）→ 寄り（オチ・感情の頂点）→ 中景/遠景（オチの余韻）
       のように引き・寄りを変化させると単調にならない
   - `characters`: 繰り返し登場させるキャラは `config/characters.yaml` に定義してキー名で参照。
     その漫画限りのキャラ・オブジェクトはsceneに直接書く
   - `bubbles`: `position` はプリセット（top / top-left / top-right / bottom / bottom-left /
     bottom-right / center）か正規化座標 `{x,y,w,h}`。`tail` は down / down-left / down-right /
     up / up-left / up-right / left / right
   - `text`: **15言語すべて**書く（ja, en, cs, de, es, fr, it, ko, pl, pt, th, uk, vi, zh, zh_Hant）。
     セリフは短く（日本語で20文字前後まで）。翻訳はClaudeが直接書いてよい
   - `attribution`: 記事のURL・著者を記載。著者は記事ページ下部やクレジットモジュールで
     確認できる。不明なら `author` を省略してよい（フッターには出典URLが必ず入る）
   - `object_class`（任意）: Safe / Euclid / Keter 等を**英語のまま**トップレベルに書く。
     タイトル下に「オブジェクトクラス：Safe」のように表示される（ラベルの翻訳は
     `config/languages.yaml` の `object_class_label` が共通で担うので、台本側では翻訳しない）
   - `panels[].caption`（任意・15言語）: そのコマの上に白地黒枠のボックスで表示される、
     SCP文書からの引用のような**淡々とした説明文**（scene/text とは別物）。実際の記事の
     Special Containment Procedures / Description の記述を要約・引用する形で書く。
     `scene`（絵の指示）や吹き出しの`text`（キャラの発話）とは違い、三人称・現在形の
     事務的な文体にする。**全コマに付ける必要はない**（起承転結の「転」＝オチのコマは
     captionを省略して間を作ると効果的。scp-999.yamlの書式見本を参照）
   - `addendum`（任意・15言語、台本トップレベル）: 最後のコマの下に表示される補遺
     （「補遺999-J：〜」）。オチを収容記録っぽく締める一言に使う
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
- キャプション枠・補遺枠は `compose.py` が白地黒枠の箱（言語非依存）を確保・描画し、
  `embed_text.py` が言語別テキストを流し込む（吹き出しと同じ「枠は先、文字は後」方式）。
  台本にcaptionが1つも無ければ枠ごと確保されず、レイアウトは元のまま
- キャラの見た目が漫画間でブレたら: 良いコマから立ち姿を切り出して `characters/refs/` に保存し、
  `config/characters.yaml` の `reference_images` に登録する
