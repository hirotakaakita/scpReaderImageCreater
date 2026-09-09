---
name: write-scp-script
description: Write a new SCP comic script (comics/queue/scp-XXX.yaml) for this project (SCP漫画ジェネレーター). Use when the user asks to write/create a script, "台本を作って", "台本作って", "N本作って", or otherwise wants a new SCP added to the queue. Encodes this project's established quality bar (verified against the live article, caption text sourced only from Special Containment Procedures / Description, canon-only characters via config/characters.yaml or local_characters, shot variety, correct addendum handling) so script quality stays consistent across sessions.
---

# SCP漫画 台本作成スキル

このスキルは `comics/queue/scp-XXX.yaml` の台本を作成するための固定手順。
このプロジェクトの品質基準（過去の失敗例から学んだルール）をそのまま守ること。
全体アーキテクチャや実装の詳細はプロジェクトの `CLAUDE.md` を参照（このスキルと
内容が食い違う場合は、より詳しい方・新しい方を優先して判断する）。

## 手順

### 1. 題材のSCPを選ぶ

- `../scpjpReaderGithubActions/local-data/scp-data.json` 等はメタデータのみで本文が
  無い。**候補が決まったら`urlJP`/`urlEN`の記事ページを直接fetchし、実際の本文
  （Special Containment Procedures / Description）を読むこと**。ローカルの記憶や
  要約だけで書かない（記事が改訂されている場合にズレる）。
- 避けるべきID: `state/used.json` に載っているID、`comics/queue/` に既にあるID。
  `state/used.json` は消さない（パイプラインが生成成功時に自動更新する重複防止台帳）。
- ユーザーが対象SCPを指定した場合はそれに従う。

### 2. 4コマ（指示があれば8コマ等）の小話を構成する

- ホラーでも軽いコメディ寄りに。グロ・残虐描写は避ける（アプリ/SNS掲載のため）。
- **記事本文の記述のみ**を根拠に描写する。公式添付画像の模倣はしない（CCライセンス
  でない画像がある）。
- **本編4コマの題材はSpecial Containment Procedures / Descriptionのみから選ぶ。
  補遺（Addendum/Addenda、実験記録、面接記録等）は本編に混ぜない**（別インシデント・
  別時系列であることが多く、混在させると1本の小話として成立しなくなる）。補遺を
  使いたければ台本トップレベルの`addendum`（1行、最後のコマ下）に留めるか、補遺
  だけで完結する別の台本にする。

### 3. `comics/queue/scp-XXX.yaml` を書く

既存の台本（`comics/queue/` か `comics/done/`）を書式見本にする。主なフィールド:

- **`scene`**（英語、絵の指示。絵柄は書かない）
  - 各コマの冒頭でショット種別を明示し、4コマで同じ画角・アングルを繰り返さない
    （例: 遠景→中景→寄り→中景/遠景、のように起承転結で引き・寄りを変化させる）。
  - そのコマに登場する人物は全員`characters`欄に載せ、sceneでも**そのキャラの
    `name`と完全に一致する名称**で呼ぶ（言い換えない）。
  - 複数人物が別々の役割・動作をするコマでは、**画面内の左右位置を明示する**
    （"On the left side of the frame, ..." / "On the right side..."）と、モデルが
    どちらのキャラがどちらの役かを安定して描き分けやすい。
  - **そのコマだけ服装・防護具等を変えたい場合は、sceneに具体的に書けば
    `characters`欄（`config/characters.yaml`/`local_characters`）のデフォルト
    服装より優先される**（`build_prompt()`側でscene優先の指示を自動的に
    プロンプトへ挿入している）。例えばハズマットスーツを着せたいコマでは、
    sceneに"a complete full-body positive-pressure hazmat suit, including a
    full sealed helmet... no bare skin visible"のように**曖昧さなく具体的に**
    書くこと。中途半端な記述（「防護服を着ている」程度）だと、キャラ欄の
    デフォルト服装（白衣等）と混ざって安定しないことを検証で確認している。
- **`notes`**（任意・panel単位・人間/Claude向けメモで生成プロンプトには入らない）
  - `refine-panel`スキルでsceneを修正する際の判断基準を、**このコマの根拠となる
    記事の一節**（要約前のcaption原文でよい）・**変えてはいけない事実**
    （captionが指定する事実で、これを崩すと引用と絵が矛盾する）・**変更可能な
    演出**（動作の種類・ショット・構図など、captionの事実に反しない範囲で
    自由に変えてよい部分）の3点に分けて短く書いておく。書いておくと、後で
    `refine-panel`が「動作の種類そのものを大胆に変えてよい」（後述）を検討する
    際に、どこまでなら変えてよいかを毎回sceneの文面から読み解き直さずに済む。
    無くても動作に支障は無いので、迷ったら省略してよい
- **`characters`**（そのコマの絵に登場する人物全員のキー名リスト）
  - **記事に書かれていない人物を勝手に創作しない**。
  - 複数の漫画で使い回すキャノン職員は`config/characters.yaml`から参照。未登録の
    職員が要る場合は http://scp-jp.wikidot.com/personnel-and-character-dossier
    から選んで`config/characters.yaml`に追加してから使う。
  - 立ち会うだけで個性が物語上重要でない役には、個性の強いキャノンキャラを流用
    せず`attending-researcher-m`/`attending-researcher-f`（無個性の汎用職員、
    `d-class`と同格）を使う。
  - **その記事にしか出ない固有の人物（SCP本人や記事内の関係者）**は台本トップ
    レベルの`local_characters`に登録し、`characters`欄からキー名で参照する
    （`config/characters.yaml`には載せない）。書式は`{name, description}`
    （旧形式・後方互換）でも`{name, appearance, default_look}`（新形式。恒常的な
    容姿`appearance`と、sceneが上書きしない限り使われる既定の服装・表情
    `default_look`を分ける。`config/characters.yaml`の現行キャラと同じ書式）
    でもよい。服装が食い違いやすいキャラ（そのコマだけ防護具を着せる等）を書く
    場合は新形式の方が安定しやすい。
  - **`characters`欄のキー順序は、sceneの文中でその人物の行動が説明される順序と
    一致させる**。順序がズレると、モデルが逆の人物にその役柄（容姿・動作）を
    割り当ててしまうことを検証で確認している（例: scp-105パネル3で発生した実例）。
  - **`local_characters`で色を指定する際は、色名だけでなく`(color RGB R,G,B)`
    の形で具体的な数値も併記する**（例: "medium gray (RGB 140,140,140)"）。
    色名だけだとコマごとに明るさ・色味がブレやすいことを検証で確認している
    （`config/characters.yaml`の既存キャラも同じ方針で記述済み）。
- **`panels[].caption`**（全コマ必須・15言語: ja, en, cs, de, es, fr, it, ko, pl,
  pt, th, uk, vi, zh, zh_Hant）
  - **要約や言い換えではなく、記事のSpecial Containment Procedures / Description
    の実際の文章にできるだけ近い形**で、記事本文を4コマぶんに分割して引用する。
  - 三人称・現在形の事務的な文体（一人称記事なら一人称のまま）。
  - captionで割り当てた記事の一節に**sceneを合わせて書く**（演出を先に決めてから
    captionを当てはめない）。
  - 4コマ目（オチ）も含め全コマに付ける。
- `attribution`: 記事URL・著者（不明なら`author`省略可）。
- `object_class`（任意）: Safe/Euclid/Keter等を英語のまま。
- `local_characters`（任意）: 上記`characters`の説明を参照。
- `addendum`（任意・15言語）: 最後のコマ下の一言。補遺の内容はここだけに留める。
- **キャラクターに吹き出しでセリフを言わせない**（`bubbles`は使わない）。

### 4. 品質チェックリスト（ファイルを書いたら必ず確認する）

- [ ] captionは全て記事のSpecial Containment Procedures / Descriptionの実際の
      文章に基づいている（補遺の内容が紛れ込んでいないか再確認）
- [ ] captionは要約・言い換えでなく、記事文の引用に近い
- [ ] 4コマの`scene`で同じ画角・アングルを繰り返していない
- [ ] 記事に無い人物を創作していない（`characters`/`local_characters`は全てキャノン
      職員または記事本文の記述に基づく人物のみ）
- [ ] `characters`欄のキー順序がsceneの行動描写順と一致している
- [ ] 複数人物が別動作をするコマでは左右位置を明示している
- [ ] `local_characters`に登録した記事固有キャラは、sceneで常に同じ名称で呼んで
      いる（言い換えていない）
- [ ] `attribution.source_url`が実在し、記事から確認したものである

### 5. 検証

```
python scripts/run_pipeline.py --id scp-XXX --mock
```

吹き出し位置・あふれ警告（`WARN: text overflow`）を確認。あふれたらcaptionを短く
する。初回は `pip install -r requirements.txt` と `python scripts/download_fonts.py`
が必要。**mock実行で作られた `output/scp-XXX/` はコミットしない**（`git checkout`
等で戻すか削除する）。

## 画像生成について

このスキルの対象は台本作成のみ。画像生成（ComfyUI経由）は別途
`python scripts/run_pipeline.py --id scp-XXX --variants N` 等で行う
（詳細はCLAUDE.mdおよび`scripts/providers/comfyui/README.md`）。
