# ComfyUI プロバイダ

`config/style.yaml` の `generation.provider: comfyui` のときに使われる。
Geminiプロバイダ（`scripts/providers/gemini/`）と同じ
`generate_image(prompt, ref_images, gen_cfg)` インターフェースで、
ローカルで起動したComfyUIのHTTP APIにワークフローを投げて画像を受け取る。

## セットアップ

1. ComfyUIをローカルで起動する（既定では `http://127.0.0.1:8188`）。
2. モデルは **Qwen-Image 2512**（fp8）。ComfyUIの `Workflow` → `Browse Templates` →
   「Text to Image (Qwen-Image 2512)」を選ぶと、以下3ファイルの自動ダウンロードを
   提案される（`models/` 配下の対応フォルダに保存される）:
   | ファイル | 保存先 |
   |---|---|
   | `qwen_image_2512_fp8_e4m3fn.safetensors` | `models/diffusion_models/` |
   | `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `models/text_encoders/` |
   | `qwen_image_vae.safetensors` | `models/vae/` |
3. 画風LoRA（`generation.comfyui.style_lora_name`、既定は
   `QwenImage_blackline.safetensors`）を `models/loras/` に配置する。
   Civitai等で配布されているQwen-Image用スタイルLoRAを差し替えれば別の画風も試せる
   （ライセンスは配布元ごとに要確認）。
4. `scripts/providers/comfyui/workflow_api_qwen_style.json` は、
   `UNETLoader` → 画風LoRA(`LoraLoaderModelOnly`) → `ModelSamplingAuraFlow` →
   `KSampler` という構成。既定は**高速化LoRA無し**（`steps: 30` / `cfg: 2` /
   `sampler_name: euler` / `scheduler: simple`）。速度を優先したい場合は
   `LoraLoaderModelOnly` ノードを追加してUNETLoaderと画風LoRAの間に高速化LoRA
   （例: `Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`）を挟み、
   `steps`/`cfg`をそのLoRAの推奨値に合わせて下げること（ただし下記の重複キャラ
   問題が再発しやすい）。

   **重要**: プロンプト文中（`generate_panels.py`の`build_prompt()`と
   `config/style.yaml`の`prompt.comfyui.*`）には`"panel"`/`"grid"`/`"frame"`/
   `"comic"`/`"manga"`/`"story"`等、複数コマ・ページ構成を連想させる単語を
   一切使わないこと（「〜にしないで」という否定形で使うのも不可）。検証の結果、
   これらの単語が入っていると、cfgを上げるほど単語への忠実度が増して、
   1枚の絵のはずが2×2グリッドの複数コマ画像として生成されてしまう問題が
   毎回発生することが分かった。逆にこれらの単語を排除した上でcfgを上げると、
   グリッド化を防ぎつつ、低cfg（`cfg: 1`、2ステップ高速化LoRA使用時など）で
   起きやすかった「1コマ内に同じキャラが重複して描かれる」問題も解消された。
5. `config/style.yaml` の `generation.provider` を `comfyui` にする。

## workflow_api.json の差し替えルール

`scripts/providers/comfyui/__init__.py` はワークフローJSON中のノードを
以下のキーで探して値を書き換える（無い場合は何もせずスキップするので、
モデルアーキテクチャが違うテンプレートに丸ごと差し替えても動く）:

| 探し方 | 対象 | 書き換える値 |
|---|---|---|
| `_meta.title == "Positive Prompt"` | CLIPTextEncode | 台本から組み立てたプロンプト文字列（必須） |
| `_meta.title == "Negative Prompt"`（あれば） | CLIPTextEncode | `generation.comfyui.negative_prompt` |
| `class_type == "CheckpointLoaderSimple"`（あれば） | SDXL系の一体型チェックポイント | `generation.comfyui.checkpoint` |
| `class_type == "UNETLoader"`（あれば） | 拡散モデル単体 | `generation.comfyui.unet_name` |
| `class_type == "CLIPLoader"`（あれば） | テキストエンコーダ単体 | `generation.comfyui.clip_name` |
| `class_type == "VAELoader"`（あれば） | VAE単体 | `generation.comfyui.vae_name` |
| `class_type == "EmptyLatentImage" / "EmptySD3LatentImage"` | 潜在画像サイズ | `generation.comfyui.width` / `height` |
| `class_type == "KSampler"` | サンプラー設定（必須） | `seed` / `steps` / `cfg` / `sampler_name` / `scheduler` |
| `class_type == "SaveImage"` | 出力ノード（必須） | （書き換えなし。結果取得に使うだけ） |

`workflow_api_qwen_style.json`（既定のフル品質ワークフロー）は実際の
「Negative Prompt」titleのCLIPTextEncodeノードを持つため、`negative_prompt` の
設定値がそのままプロンプトに反映される。一方、Z-Image Turbo等の高速化LoRA前提の
公式テンプレートはネガティブプロンプトの代わりに `ConditioningZeroOut`
（Positiveの条件付けをゼロ化したものをそのままnegativeに使う）を使っており、
その場合は `negative_prompt` の設定値は無視される（`workflow_api.json` 参照）。

IPAdapterやControlNetなど画像入力ノードを足せば、`ref_images`
（キャラ参照画像・直前コマ画像）を渡すよう拡張することも可能
（現状のQwen-Image用ワークフローは画像入力が無いため `ref_images` は無視される）。

## 挙動

1. `workflow_api.json` を読み込み、上表のノードを書き換える
2. `POST {server}/prompt` でキューに投入し `prompt_id` を受け取る
3. `GET {server}/history/{prompt_id}` を `poll_interval_seconds` 間隔で
   ポーリングし、結果が出るまで待つ（`timeout_seconds` で打ち切り）
4. `GET {server}/view` で生成画像を取得する
5. 接続エラー・タイムアウト・ノード不備は `max_retries` 回まで
   `retry_wait_seconds` ずつ待ってリトライする

## 制約

- 現状の `--export-prompts`（Google AI Studio向けの手動書き出し）は
  Gemini向けの文言のままなので、ComfyUI利用時はAPI経由の自動生成
  （`python scripts/run_pipeline.py --id scp-XXX`）を使うこと。
