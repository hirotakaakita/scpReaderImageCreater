# SCP漫画ジェネレーター

SCP記事を題材にした多言語コマ漫画を生成する。台本作り・画像生成とも**すべてローカルで
Claude Codeが行う**（自動化なし）。全体像はREADME.md参照。

## 台本作成の手順（「台本を作って」「N本作って」と言われたらこれを実行）

1. 題材のSCPを選ぶ
   - 記事データ: `../scpjpReaderGithubActions/local-data/scp-data.json` ほか言語別ディレクトリ。
     ただしこれは記事一覧のメタデータ（タイトル・URL等）のみで本文は含まれていない。
     **台本執筆時は`urlJP`/`urlEN`の記事ページを直接取得し、そこにある実際の本文
     （Special Containment Procedures / Description等）を根拠にすること**。ローカルの
     要約や記憶だけで書くと、記事が改訂されている場合に内容がズレる（実例:
     scp-105は台本作成時点の記事情報が古く、実際の記事にある外見描写やSCP-105-Bの
     カメラの型番等が反映されていなかった）
   - **`state/used.json`（生成済みSCPの記録）にあるIDと、`comics/queue/` に積まれているIDは避ける**。
     used.jsonは`run_pipeline.py`が生成成功時に自動更新する。**消すと重複生成の恐れがあるので消さない**
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
     - SCP本人など**characters.yamlに載せない記事固有のキャラ**を複数コマに登場させる
       場合、外見の説明は最初のコマだけでなく**毎コマのsceneに繰り返し書く**こと
       （characters.yamlのキャラはコマごとに自動でdescriptionが挿入されるが、
       記事固有キャラはその仕組みが無いため、書き忘れたコマだけ見た目がブレる）
   - `characters`: **記事に書かれていない人物を勝手に創作しない**。財団職員として
     登場させるなら、SCP財団正史（キャノン）に実在する人物を使う。選定元は
     `config/characters.yaml`（すでに登録済みのキャノン職員はキー名で参照するだけでよい）。
     未登録の職員を新たに使いたい場合は
     http://scp-jp.wikidot.com/personnel-and-character-dossier
     （財団職員・要注意人物の公式人物ファイル集）から選び、`config/characters.yaml`に
     追加してから参照する（詳細は同ファイル冒頭のコメント参照）。記事自体に固有の
     人物（SCP本人や記事内の関係者等）は、その記事の記述に基づいてsceneに直接書く
     （characters.yamlには載せない。他の漫画で使い回すキャラのためのファイルのため）
   - **キャラクターに吹き出しでセリフを言わせない**（`bubbles`は使わない）。台本のスタイルは
     「収容記録を模した無言の4コマ＋各コマ上の解説文ボックス」。演出は`scene`（表情・動作）と
     `caption`の文章だけで作る
   - `panels[].caption`（**全コマ必須・15言語**）: そのコマの上に白地黒枠のボックスで表示される、
     SCP文書からの引用のような**淡々とした説明文**。**要約や言い換えではなく、記事の
     Special Containment Procedures / Descriptionの実際の文章にできるだけ近い形**で、
     記事本文を4コマぶんに分割して引用する（1文をまるごと1コマに、長い場合は2〜3コマに
     分けてもよい）。三人称・現在形の事務的な文体（一人称記事なら一人称のまま引用してよい。
     scp-426.yamlの書式見本を参照）。`scene`（絵の指示）とは別物だが、**その引用が何を
     言っているかを絵で視覚化する背景として`scene`を書く**（漫画の演出を先に決めてから
     captionを付けるのではなく、captionで割り当てた記事の一節に合わせてsceneを書く）。
     4コマ目（オチ）も含め**全てのコマに付ける**
   - `attribution`: 記事のURL・著者を記載。著者は記事ページ下部やクレジットモジュールで
     確認できる。不明なら `author` を省略してよい（フッターには出典URLが必ず入る）
   - `object_class`（任意）: Safe / Euclid / Keter 等を**英語のまま**トップレベルに書く。
     タイトル下に「オブジェクトクラス：Safe」のように表示される（ラベルの翻訳は
     `config/languages.yaml` の `object_class_label` が共通で担うので、台本側では翻訳しない）
   - `addendum`（任意・15言語、台本トップレベル）: 最後のコマの下に表示される補遺
     （「補遺999-J：〜」）。オチを収容記録っぽく締める一言に使う
4. 検証: `python scripts/run_pipeline.py --id scp-XXX --mock` を実行し、
   吹き出しの位置・あふれ警告（`WARN: text overflow`）を確認。あふれたらセリフを短くする
   - 初回は `pip install -r requirements.txt` と `python scripts/download_fonts.py` が必要
   - **mock実行で作られた output/scp-XXX/ はコミットしない**（`git checkout`等で戻すか削除）

## 実装メモ

- 画像生成の実行部分（API呼び出し）はプロバイダ別に `scripts/providers/<name>/` に
  切り出してある（`gemini`: Nano Banana、`comfyui`: ローカルComfyUI）。切替は
  `config/style.yaml` の `generation.provider`。各フォルダの`README.md`にセットアップ
  手順あり。新プロバイダを足す場合は`generate_image(prompt, ref_images, gen_cfg)`を
  実装して`scripts/providers/__init__.py`に登録する
- 生成プロンプトの組み立ては `scripts/generate_panels.py` の `build_prompt()`。
  順序: style_prompt → キャラ定義 → caption(en、絵が何を描くべきかの根拠) → scene →
  吹き出しスペース確保の指示 → 構図規則 → 文字禁止規則。**caption(en)を必ず絵に一致させる
  ため、captionの英語文をそのままプロンプトに含めている**（scene単独では絵が
  captionの内容とズレることがあるため、ズレ防止の二重根拠）。scene執筆時から
  captionの内容と食い違わないよう意識すること
- 画像には**一切文字を描かせない**。タイトル・セリフ・ライセンスはPython（Pillow）が後から描く
- 言語別フォントに無いグリフ（タイ語フォントのラテン文字等）は `lib/textutil.py` の
  FontSetがNotoSansへ自動フォールバックする
- コマ座標は `output/<id>/meta.json` 経由で `embed_text.py` に渡る。
  `layout.yaml` を変えたら `--skip-generate` で合成・埋め込みだけ再実行できる
- キャプション枠は各コマの絵の**内側**（デフォルト左上、`caption_position`で
  `top-right`/`bottom-left`/`bottom-right`に変更可）に、文字量に合わせて縮む箱として
  `embed_text.py`が言語別に描く（吹き出しのdraw_speechと同じ「最大領域→文字に合わせて縮小」
  方式。`compose.py`側では確保しない）。補遺枠は従来通り`compose.py`が最終コマ下に確保する
- キャラの見た目が漫画間でブレたら: 良いコマから立ち姿を切り出して `characters/refs/` に保存し、
  `config/characters.yaml` の `reference_images` に登録する
