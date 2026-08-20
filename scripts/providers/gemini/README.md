# Gemini (Nano Banana) プロバイダ

`config/style.yaml` の `generation.provider: gemini` のときに使われる。

## セットアップ

1. `GEMINI_API_KEY` 環境変数にAPIキーを設定する。
2. `config/style.yaml` の `generation.gemini.model` でモデルを選ぶ
   （無料枠検証中は `gemini-2.5-flash-image`、課金有効化後は
   `gemini-3-pro-image-preview` へ）。

## 挙動

- `generate_image(prompt, ref_images, gen_cfg)` が `google-genai` SDK経由で
  Gemini画像生成APIを呼び出す。
- キャラクター参照画像・直前コマ画像（`ref_images`）を渡すことで、
  コマ間のキャラクター一貫性を上げている
  （`generation.use_previous_panels_as_reference` / `max_reference_images`）。
- レート制限・一時エラー時は `generation.gemini.max_retries` 回まで
  指数的な待機を挟んでリトライする。

## APIキーが無い場合

`python scripts/run_pipeline.py --id scp-XXX --export-prompts` で
`output/<id>/prompts/` にプロンプト・参照画像・手順書を書き出し、
Google AI Studio (aistudio.google.com) で手動生成できる。
