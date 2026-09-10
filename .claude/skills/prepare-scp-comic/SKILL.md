---
name: prepare-scp-comic
description: End-to-end pipeline that turns one or more SCP names/numbers into ComfyUI-ready generation prompts. Given "scp-XXX" (or a comma-separated list), it runs write-scp-script → review-scp-script (Codex) → mock verification → prompt export, leaving output/scp-XXX/prompts/panel_N.txt ready to feed to ComfyUI. Use when the user says "scp-XXXの漫画を用意して" / "scp-XXXをComfyUIに渡せる状態にして" / "台本からプロンプトまで一気に" / hands over a batch of SCP numbers to prep. Does NOT run image generation itself.
---

# SCP名 → ComfyUI用プロンプト（一連の流れ）

SCPの名前・番号を渡されたら、**記事本文の取得から、ComfyUIに渡せる
生成プロンプト（`output/scp-XXX/prompts/panel_N.txt`）の書き出しまで**を
一気通貫で行うスキル。既存の `write-scp-script` / `review-scp-script` と
`run_pipeline.py` のコマンドを、正しい順序と後片付け込みで束ねたもの。

**画像生成そのもの（ComfyUI呼び出し）はこのスキルの対象外**。プロンプトが
揃ったら、あとは別途 `python scripts/run_pipeline.py --id scp-XXX --variants N`
で候補生成→人手選別、という運用（CLAUDE.md参照）。

## 入力

- SCP番号ひとつ（例: `scp-096`）、または複数（カンマ区切り、例: `scp-096,scp-173,scp-682`）
- コマ数の指定があればそれに従う（デフォルト4コマ）

## 前提の確認（最初に1回）

- `python --version` が通る。初回は `pip install -r requirements.txt` と
  `python scripts/download_fonts.py` が必要。
- Codex CLI: `npx --yes @openai/codex@latest --version` が通るか確認。
  通らなければ `review-scp-script` のサブエージェント版フォールバックを使う。
- **ComfyUIは起動していなくてよい**（このスキルは画像生成をしないため）。

## 手順（SCP 1本ごとに、以下を順に実行）

### 1. 台本を書く — `write-scp-script`

`write-scp-script` スキルを読み込み、その手順に**厳密に**従って
`comics/queue/scp-XXX.yaml` を新規作成する。要点（詳細はスキル本体を参照）:

- 記事本文（`http://scp-wiki.wikidot.com/scp-XXX`、日本記事なら `scp-jp.wikidot.com`）を
  **WebFetchで実際に取得**し、Special Containment Procedures / Description の
  実際の文章のみを根拠にcaptionを書く（要約・言い換え禁止、補遺は本編に混ぜない）。
- 記事固有の人物は `local_characters` に `{name, appearance, default_look}` 形式で。
  汎用職員は `config/characters.yaml` の `attending-researcher-m/f` `d-class` `mtf-agent`。
- 4コマの起承転結、画角バリエーション、`characters` 欄のキー順序、15言語caption。
- **YAML文字列は必ず straight quote `"` で囲む。スマートクォート `“ ”` は使わない**
  （YAMLパースエラーの主因。文字列内に `:` を含む場合は必ずダブルクオート）。

### 2. 物語構成レビュー — `review-scp-script`

`review-scp-script` スキルを読み込み、その手順で **Codex（無ければサブエージェント）**に
4コマとしての起承転結・矛盾・caption/scene不一致・画角の重複をレビューしてもらう。

- **並列で複数SCPを処理している場合、一時ファイルのパスは必ずSCP固有の名前にする**
  （例: `/tmp/review_prompt_scp-096.txt`）。`/tmp/review_prompt.txt` の共通名は使わない。
- 複数SCPをまとめてレビューする場合は、対象パスを全部並べて1回のCodex呼び出しで
  レビューさせてよい（このセッションで15〜20本/回まで問題なく処理できた実績あり）。
- 返ってきた指摘は**全て鵜呑みにしない**。記事本文を実際に確認していない外部
  エージェントが事実関係を誤認しているケースは退ける。妥当な指摘（明確な
  caption/scene矛盾・時系列の飛躍・画角の反復・規則違反）だけ台本に反映する。
- 台本を直したら、変更点を一言記録する。

### 3. レイアウト検証（mock）

```
python scripts/run_pipeline.py --id scp-XXX --mock
```

- `WARN: text overflow` が出たら、そのコマ・言語のcaptionを短くする
  （**記事原文の分割を先に検討**。要約はしない。scp-426.yaml等の書式見本参照）。
- 複数SCPをまとめて検証する場合は `--id scp-A,scp-B,scp-C --mock`（カンマ区切り対応済み。
  内部で1本ずつ順に処理される）。
- **mock生成物は必ず後片付けする**（`--mock` は本番と同じ実パスにプレースホルダー画像を
  書くため）:
  ```
  rm -f output/scp-XXX/base.png output/scp-XXX/meta.json output/scp-XXX/*.png \
        output/scp-XXX/panels/panel_*.png output/scp-XXX/panels/prompts.json
  git checkout -- index.json   # mock時はbuild_indexはスキップされるが念のため
  ```
  対象comicが `comics/done/` にあり出力がコミット済みなら `rm` でなく
  `git checkout -- output/scp-XXX/` で戻す。

### 4. ComfyUI用プロンプトの書き出し

```
python scripts/run_pipeline.py --id scp-XXX --export-prompts
```

- `output/scp-XXX/prompts/panel_1.txt` 〜 `panel_4.txt` と `README.txt` が生成される。
  これが**ComfyUIに渡す最終的な生成プロンプト**。`build_prompt()` の出力そのもの
  （style_prompt + キャラ定義 + caption(en) + scene + 余白確保指示 + 構図規則 + 文字禁止規則）。
- 複数SCPは `--id scp-A,scp-B --export-prompts` でまとめて。
- `output/scp-XXX/prompts/` はコミット対象外（`panels_temp/` と同じ扱いの作業成果）。

### 5. 完了報告

各SCPについて「台本OK / スキップ（理由）」「Codexレビューで反映した修正」
「`output/scp-XXX/prompts/` にプロンプト書き出し済み」を報告する。
**git add/commit/push はこのスキルでは行わない**（呼び出し側の判断）。

## この後の流れ（このスキルの範囲外）

プロンプトが揃ったら、画像生成は別途:

```
python scripts/run_pipeline.py --id scp-XXX --variants 4    # 候補生成（ComfyUI要起動）
# → 人手で候補を選び output/scp-XXX/panels/panel_N.png にコピー
python scripts/run_pipeline.py --id scp-XXX --skip-generate  # 合成・15言語埋め込み・done移動
```

- **複数SCPの候補生成を並列で走らせないこと**（ComfyUIのキュー詰まり・RAM逼迫を確認済み。
  `--id` のカンマ区切りは内部で1本ずつ直列処理する）。
- 1コマだけ気に入らない場合は `--panel N --variants 4`（`--panel` を付け忘れると全コマ上書き）。
- コマの局所的な乱れは ComfyUI画面上のインペイントで直す（`scripts/providers/comfyui/README.md`）。

## 大量バッチのときの注意（このセッションでの実地知見）

- **サブエージェントを10並列で走らせるとセッションのレート制限に当たって全滅する**。
  4並列×10本程度の波に分け、波の間で完了を待つこと。Codexレビューは個別ではなく
  全台本が揃ってから一括（15〜20本/回）で回すとレート消費を抑えられる。
- サブエージェントに任せる場合、各エージェントに「担当SCPの固定リスト（重複なし）」と
  「SCP固有の一時ファイル名」を渡し、`--variants` 等の画像生成コマンドは絶対に
  実行しないよう明記する。
