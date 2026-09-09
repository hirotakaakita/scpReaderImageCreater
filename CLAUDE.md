# SCP漫画ジェネレーター

SCP記事を題材にした多言語コマ漫画を生成する。台本作り・画像生成とも**すべてローカルで
Claude Codeが行う**（自動化なし）。全体像はREADME.md参照。

## 台本作成の手順（「台本を作って」「N本作って」と言われたらこれを実行）

1. 題材のSCPを選ぶ
   - 記事データ: `../scpjpReaderGithubActions/local-data/scp-data.json` ほか言語別ディレクトリ。
     ただしこれは記事一覧のメタデータ（タイトル・URL等）のみで本文は含まれていない。
     **台本執筆時は`urlJP`/`urlEN`の記事ページを直接取得し、そこにある実際の本文
     （Special Containment Procedures / Description等）を根拠にすること**。
     **補遺（Addendum）は4コマ本編の題材にしない**（後述）。ローカルの
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
     - **そのコマに登場する人物は全員、後述の`characters`欄に載せたキー名と完全に一致する
       名称でsceneにも書く**（例: `local_characters`に`SCP-105`として登録したなら、
       sceneでも常に"SCP-105"と書き、"the subject"等の言い換えをしない）。名称を一致
       させることで、画像生成プロンプトに自動挿入される容姿description（後述）と
       scene中の呼び方がズレず、コマごとに容姿の説明を手書きし直す必要もなくなる
     - 複数人物が特定の役割・動作（誰が何を持つ、誰が何をする等）を担うコマでは、
       **sceneの左右位置の明示（"On the left..." / "On the right..."）を検討する**。
       画像生成モデルは同じ文中に複数の行動主体がいると、どちらがどちらの役かを
       取り違えることがある（重複キャラ問題や役割の入れ替わり）。位置を明示すると
       「誰が画面のどちら側で何をするか」は安定するが、**「どちらの容姿がどちらの
       役を演じるか」は`characters`欄（後述）に書いた順序が決める**ことを検証で
       確認した——sceneの文中で最初に行動が説明される人物を`characters`欄でも
       先頭に書くこと（順序がズレていると、sceneの記述と逆の人物がその役を演じて
       しまう。実例: scp-105のパネル3で発生）
   - `characters`（**そのコマの絵に登場する人物全員**のキー名リスト。SCP本人・記事内の
     関係者・財団職員を問わず、絵に描かれる人物は漏れなくここに書く。**sceneの文中で
     行動が説明される順序と同じ順序で書く**——理由は上記参照）:
     - 複数の漫画で使い回すキャノン職員は`config/characters.yaml`にキー名で登録済みの
       ものを参照する。**記事に書かれていない人物を勝手に創作しない**。財団職員を
       登場させるなら、SCP財団正史（キャノン）に実在する人物を使う（選定元:
       http://scp-jp.wikidot.com/personnel-and-character-dossier
       財団職員・要注意人物の公式人物ファイル集。追加登録の詳細は`config/characters.yaml`
       冒頭のコメント参照）。単に「立ち会う職員が1人いる」程度で、特定の個性・見た目が
       物語上重要でない役には、`dr-sage-west`のような個性の強いキャノンキャラを流用せず
       `attending-researcher-m`/`attending-researcher-f`（無個性・黒髪の汎用職員、
       `d-class`と同じ位置づけ）を使う
     - **その記事にしか登場しない固有の人物（SCP本人や記事内の関係者等）**は、
       `config/characters.yaml`には載せず、台本トップレベルの`local_characters`
       （その台本だけのローカルなキャラ定義。書式は`config/characters.yaml`と同じ
       `{name, description}`）に書き、`characters`欄からキー名で参照する。こうすると
       `config/characters.yaml`のキャラと同様に、そのキャラの容姿descriptionが
       登場する全コマのプロンプトへ自動挿入されるため、sceneに容姿を手書きし直す
       必要がなくなり、コマ間で容姿がブレる事故も防げる（書式は`config/characters.yaml`
       の各エントリと同じなので、そちらを参照）。**色を指定する際は色名だけでなく
       `(color RGB R,G,B)`の形で具体的な数値も併記する**（例: "medium gray (RGB
       140,140,140)"）。色名だけだとコマごとに明るさ・色味がブレやすいことを
       検証で確認している
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
     - **本編4コマの題材はSpecial Containment Procedures / Descriptionのみから選ぶ。
       補遺（Addendum/Addenda、実験記録、面接記録等の付随文書）の内容は本編captionに
       混ぜない**。補遺は別インシデント・別時系列のサブエピソードであることが多く、
       Descriptionの内容と補遺の内容を1つの4コマに混在させると、時系列や場面が
       ズレて1本の小話として成立しなくなる（実例: scp-105で発生）。補遺の内容を
       使いたい場合は、4コマとは別に台本トップレベルの`addendum`（1行・最後のコマ下）
       に留めるか、補遺だけで完結する別の台本として独立させる
   - `local_characters`（任意・台本トップレベル）: その台本だけに登場する記事固有の
     人物（SCP本人や記事内の関係者等）の定義。キー: `{name, description}`
     （書式は`config/characters.yaml`と同じ）。`panels[].characters`から
     キー名で参照する（詳細は上記`characters`欄の説明を参照）
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
5. 画像生成（現状、生成精度がまだ安定しないため候補を複数出して人手で選ぶ運用）:
   `python scripts/run_pipeline.py --id scp-XXX --variants N` を実行すると、コマごとに
   N枚の候補が `output/scp-XXX/panels_temp/panel_N_vM.png` に生成され、そこで停止する
   （`panels/panel_N.png`はまだ書き換わらない）。ユーザーが候補を目視で選び、気に入った
   1枚を `output/scp-XXX/panels/panel_N.png` としてコピーし直したら、
   `python scripts/run_pipeline.py --id scp-XXX --skip-generate` で合成・15言語埋め込み
   まで実行する。`panels_temp/`はコミットしない（`.gitignore`済み）
   - **1コマの中の一部分だけがおかしい場合**（模様の乱れ・局所的な色ズレ等）は、
     そのコマ全体を再生成せず、ComfyUI画面上でのインペイントで直す方針
     （Pythonでの画像後処理は行わない）。手順は
     `scripts/providers/comfyui/README.md`の「生成済みコマの局所的な修正
     （インペイント）」参照

## 実装メモ

- 画像生成の実行部分（API呼び出し）はプロバイダ別に `scripts/providers/<name>/` に
  切り出してある。現状は `comfyui`（ローカルComfyUI）のみ使用（Geminiプロバイダは
  削除済み）。`config/style.yaml` の `generation.provider` で切替可能な設計は残して
  あり、`scripts/providers/comfyui/README.md`にセットアップ手順あり。新プロバイダを
  足す場合は`generate_image(prompt, ref_images, gen_cfg)`を実装して
  `scripts/providers/__init__.py`に登録する
- 生成プロンプトの組み立ては `scripts/generate_panels.py` の `build_prompt()`。
  順序: style_prompt → キャラ定義 → caption(en、絵が何を描くべきかの根拠) → scene →
  キャプション/吹き出しスペース確保の指示 → 構図規則 → 文字禁止規則。**caption(en)を
  必ず絵に一致させるため、captionの英語文をそのままプロンプトに含めている**（scene
  単独では絵がcaptionの内容とズレることがあるため、ズレ防止の二重根拠）。scene執筆時
  からcaptionの内容と食い違わないよう意識すること
  - スペース確保の指示は、台本にcaptionがあれば`embed_text.caption_position_for()`と
    同じ計算で実際に重なるキャプション枠の位置（top-left/top-right等）を、bubblesが
    あればその位置も、合わせて空けるよう求める（現行の台本はbubblesを使わずcaptionのみ
    運用しているため、caption分の余白確保が無いとこの指示自体が実質死んでいた）
- キャラ定義の挿入は `lookup_character()` が担う。`panels[].characters`のキー名を
  台本の`local_characters`（記事固有キャラ）→`config/characters.yaml`（使い回しキャラ）
  の順で探し、見つかった`description`を「Characters appearing in this image」欄に
  `<キー名>: <description>` の形で列挙する（キー名を明示的にdescriptionへ結び付け、
  sceneでの呼び方との対応をモデルに直接渡す。順序一致だけに頼らない二重の根拠）。
  両方の情報源を同じ仕組みで扱うため、`local_characters`に登録した記事固有キャラ
  （SCP本人含む）も、キャノン職員と同様にコマごとの容姿説明の自動挿入・一貫性維持の
  対象になる。**存在しないキー名を`characters`欄に書くと生成前にエラーで止まる**
  （黙って容姿説明が抜け落ちる事故を防ぐため）
- **キャラ欄の服装とsceneの服装が食い違う場合はsceneを優先**するよう、
  `build_prompt()`がキャラ欄の直前に明示の優先指示を挿入している（例:
  ハズマットスーツを着せたいコマでキャラ欄のデフォルト服装＝白衣と衝突し、
  服装が安定しない問題があったための対策）。台本側でそのコマだけ服装を
  変えたい場合は、scene側に具体的に（曖昧さなく）書けばよい
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
