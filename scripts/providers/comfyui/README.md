# ComfyUI プロバイダ

`config/style.yaml` の `generation.provider: comfyui` のときに使われる。
Geminiプロバイダ（`scripts/providers/gemini/`）と同じ
`generate_image(prompt, ref_images, gen_cfg)` インターフェースで、
ローカルで起動したComfyUIのHTTP APIにワークフローを投げて画像を受け取る。

## セットアップ

1. ComfyUIをローカルで起動する（既定では `http://127.0.0.1:8188`）。
2. モデルは **Z-Image Turbo**（Tongyi-MAI、6B、Apache 2.0、8ステップ蒸留で
   高速・アニメ調にも強い）。**ComfyUIに標準搭載の公式テンプレートで導入する
   のが一番簡単**（Civitai等でマージ版を探す必要は無い）:
   - ComfyUIのメニューから `Workflow` → `Browse Templates`（またはトップ画面の
     テンプレート一覧）を開き、**「Text to Image (Z-Image-Turbo)」**を選ぶ
   - 選ぶと以下3ファイルの自動ダウンロードを提案される（実行すると
     `models/` 配下の対応フォルダに保存される）:
     | ファイル | 保存先 |
     |---|---|
     | `z_image_turbo_bf16.safetensors` | `models/diffusion_models/` |
     | `qwen_3_4b.safetensors` | `models/text_encoders/` |
     | `ae.safetensors` | `models/vae/` |
   - `scripts/providers/comfyui/workflow_api.json` は、この公式テンプレートの
     ノード構成（`UNETLoader` + `CLIPLoader` + `VAELoader` +
     `ModelSamplingAuraFlow` + `KSampler` 等）をAPI形式で再現したもの。
     上記3ファイルのデフォルトファイル名と一致していればそのまま動く
   - VRAMが厳しい場合は同テンプレート内でfp8/GGUF版への差し替えも案内される
3. `config/style.yaml` の `generation.provider` を `comfyui` にする
   （`generation.comfyui` の `unet_name` / `clip_name` / `vae_name` /
   `steps: 8` / `cfg: 1` / `sampler_name: res_multistep` / `scheduler: simple`
   はZ-Image Turbo公式テンプレートの推奨値。ファイル名を変えた場合はそこも合わせる）。

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

Z-Image Turbo公式テンプレートはネガティブプロンプトの代わりに
`ConditioningZeroOut`（Positiveの条件付けをゼロ化したものをそのままnegativeに使う）
を使っているため、`negative_prompt` の設定値は無視される。SDXL系など
実際に「Negative Prompt」というtitleのCLIPTextEncodeノードを持つワークフローに
差し替えれば、その値が反映されるようになる。

IPAdapterやControlNetなど画像入力ノードを足せば、`ref_images`
（キャラ参照画像・直前コマ画像）を渡すよう拡張することも可能
（現状のZ-Image Turboテンプレートは画像入力が無いため `ref_images` は無視される）。

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
