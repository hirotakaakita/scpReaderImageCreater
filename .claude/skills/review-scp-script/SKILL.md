---
name: review-scp-script
description: Review a drafted SCP comic script (comics/queue/scp-XXX.yaml) for 4-panel narrative structure (起承転結) and internal consistency before it goes to image generation, consulting Codex CLI when available or a subagent as a fallback. Use as the final step of write-scp-script, right after drafting a script and before the --mock verification step, or whenever asked to "物語をチェックして"/re-review an already-queued script.
---

# 台本の物語構成レビュー

`write-scp-script`で書いた台本（`comics/queue/scp-XXX.yaml`）を、画像生成にかける前に
**もう一つの視点**で確認するスキル。自分（台本を書いた本人）だけの判断だと見落としが
出やすい「4コマとして起承転結になっているか」「物語として破綻していないか」を、
別のエージェント（Codexまたはサブエージェント）に相談してチェックしてもらう。

**このスキルは台本を直接書き換えない**。指摘を持ち帰り、`write-scp-script`の基準に
照らして妥当なものだけ台本に反映するのは呼び出し側（Claude自身）の仕事。

## いつ使うか

- `write-scp-script`で台本を書き終えた直後、`--mock`検証より前（新規台本のデフォルト手順）
- 既にqueue/doneにある台本を「物語として大丈夫か見直して」と言われたとき
- 複数台本をまとめてレビューしたいとき（対象パスを複数渡せばよい）

## 手順

### 1. 相談相手を決める（Codex優先、無ければサブエージェント）

まず Codex CLI が使えるか確認する:

```
npx --yes @openai/codex@latest --version
```

エラーなくバージョンが返れば使える。**使えない場合（未インストール・認証エラー・
ネットワーク不通など、何であれ失敗したら）は、Task/Agentツールで`general-purpose`
サブエージェントを立てて代わりに相談する**（下記「サブエージェント版のプロンプト」参照）。
どちらか一方が必ず動く前提で、両方失敗したらユーザーに報告して止める。

### 2. Codex版: レビューを依頼する

**重要**: プロンプトをCLI引数に直接渡すと改行で切り詰められることがある
（このプロジェクトでの実検証で確認済み）。必ずファイルに書いてstdin経由で渡す。

```bash
cat > /tmp/review_prompt.txt << 'EOF'
以下のSCP漫画4コマ台本ファイルを読んで、レビューしてください。
編集はせず、指摘だけをまとめてください。

対象ファイル: comics/queue/scp-XXX.yaml
（複数ある場合はここに全パスを列挙する）

確認してほしい観点:
1. 4コマとして起承転結になっているか（1コマ目=導入、2コマ目=展開、
   3コマ目=転（気付き/異変）、4コマ目=結（オチ）の流れが成立しているか。
   このプロジェクトの意図は「淡々とした収容記録を読み進めるうちに、実は
   ×××だったと気付く」という段階的な気付きの構成）
2. 物語として矛盾・飛躍がないか（3コマ目と4コマ目の間で状況が
   説明なく変わりすぎていないか等）
3. 各panelのcaptionが実際にSpecial Containment Procedures / Descriptionの
   文章に基づいていそうか（不自然な言い換え・創作が無いか、文面から判断できる範囲で）
4. sceneの記述がcaptionの内容と食い違っていないか
5. 同じ画角・構図が4コマで繰り返されていないか（CLAUDE.md方針）

指摘があれば「コマ番号: 問題点 → 提案」の形で列挙してください。
問題が無ければ「問題なし」とだけ答えてください。
EOF
npx --yes @openai/codex@latest exec -s read-only - < /tmp/review_prompt.txt
```

Codexはファイルを直接読めるので、台本のパスを渡せば本文を渡す必要はない。

### 3. サブエージェント版: Codexが使えない場合

Task（Agent）ツールで`general-purpose`エージェントを起動し、上記と同じ5観点を
渡す。サブエージェントもRead/Grepでファイルを直接読めるので、対象パスを渡せば足りる。
プロンプト例:

```
comics/queue/scp-XXX.yaml を読んで、SCP漫画4コマ台本としてレビューしてください。
編集はせず、指摘だけをまとめて報告してください。確認観点:
1. 4コマとして起承転結になっているか（1=導入→2=展開→3=転（気付き/異変）→4=結（オチ））
2. 物語として矛盾・飛躍がないか
3. 各panelのcaptionが記事のSpecial Containment Procedures / Descriptionの文章に
   基づいていそうか（不自然な言い換え・創作が無いか）
4. sceneの記述がcaptionの内容と食い違っていないか
5. 同じ画角・構図が4コマで繰り返されていないか
指摘は「コマ番号: 問題点 → 提案」の形で。問題が無ければ「問題なし」とだけ返してください。
```

### 4. 指摘を反映する

返ってきた指摘を`write-scp-script`の品質基準（CLAUDE.md・write-scp-script/SKILL.md）
に照らして判断する。**全ての指摘を無批判に採用しない**——的外れな指摘（記事を実際に
確認していない外部エージェントが、記事本文の事実関係を誤って「矛盾」と判定するケース等）
は退けてよい。妥当な指摘のみ台本に反映し、scene/captionを修正する。

修正した場合は、変更点を一言でユーザーに報告する（例:「Codexの指摘で2コマ目と3コマ目の
つながりが唐突と分かったので、3コマ目の書き出しに軽い接続を追加しました」）。

### 5. 次の手順へ

台本が固まったら、`write-scp-script`の残り手順（品質チェックリスト→`--mock`検証）に戻る。
このスキル単体では画像生成もmock検証も行わない。
