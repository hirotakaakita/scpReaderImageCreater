# ComfyUI プロバイダ

`config/style.yaml` の `generation.provider: comfyui`（現状唯一のプロバイダ）で
使われる。`generate_image(prompt, ref_images, gen_cfg)` インターフェースで、
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
   `UNETLoader` → 高速化LoRA「Turbo LoRA」(`LoraLoaderModelOnly`) → 画風LoRA
   「Style LoRA」(`LoraLoaderModelOnly`) → `ModelSamplingAuraFlow` →
   `KSampler` という構成。既定は**2ステップ高速化LoRA
   `Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors`使用**
   （`steps: 2` / `cfg: 1` / `sampler_name: euler` / `scheduler: simple`、
   `style_lora_strength: 1.0`）。1コマ数十秒で生成できるが、**1コマ内に同じ
   キャラが重複して描かれる／2人の髪色などの属性が混同される問題が確率的に
   発生する**（検証では4コマ中1コマ程度）。steps=4/8も試したが、いずれも
   安定した改善は確認できなかった（steps=8はある検証回では3/3成功したが
   再現せず、steps数を上げること自体に確実な効果は無いと判断）ため、速度を
   優先してsteps=2に戻している。生成のたびに目視確認し、発生したコマだけ
   再生成（リロール）する運用が前提。安定性を優先する場合は
   「Turbo LoRA」ノードを外してStyle LoRAの`model`入力をUNET Loaderに直結し、
   `steps: 30` / `cfg: 2` / `style_lora_strength: 1.4`に戻すこと（1コマ数分〜
   十数分かかるが重複キャラ・属性混同は起きにくい）。`style_lora_strength`は
   steps数に応じて調整が要る（steps=30だとベースモデル自身の色彩表現が乗って
   モノクロ表現が薄まるため1.4まで上げて補正しているが、steps=2〜8程度の
   高速化LoRA構成でこの値のままだと逆に線が甘く・不確かになる）。

   **重要**: プロンプト文中（`generate_panels.py`の`build_prompt()`と
   `config/style.yaml`の`prompt.comfyui.*`）には`"panel"`/`"grid"`/`"frame"`/
   `"comic"`/`"manga"`/`"story"`等、複数コマ・ページ構成を連想させる単語を
   一切使わないこと（「〜にしないで」という否定形で使うのも不可）。検証の結果、
   これらの単語が入っていると、cfgを上げるほど単語への忠実度が増して、
   1枚の絵のはずが2×2グリッドの複数コマ画像として生成されてしまう問題が
   毎回発生することが分かった（cfg=1でも稀に発生した）。これは高速化LoRAの
   有無やcfg/stepsとは別軸の問題で、重複キャラ問題（上記）とは原因が異なる。
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

`workflow_api_qwen_style.json`（既定のワークフロー）は実際の
「Negative Prompt」titleのCLIPTextEncodeノードを持つため、`negative_prompt` の
設定値はプロンプトとしては常にエンコードされる。ただし既定の`cfg: 1`では
CFGの数式上negative項が結果に影響しない（cfgを2以上に上げれば効くようになる）。
一方、Z-Image Turbo等の高速化LoRA前提の公式テンプレートはネガティブプロンプト
の代わりに `ConditioningZeroOut`（Positiveの条件付けをゼロ化したものをそのまま
negativeに使う）を使っているものもある（`workflow_api.json` 参照）。

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

## 生成済みコマの局所的な修正（インペイント）

生成済みの1コマの中の一部分だけがおかしい（不自然な模様・色ズレ等）場合、
そのコマ全体を再生成し直す代わりに、ComfyUIの画面上でインペイント（該当範囲
だけ塗り替え）して直す。Pythonでの画像後処理（座標をコードで目測して塗り替える
等）は行わない方針（過去に試したが、範囲の目測がズレやすく精度・保守性の面で
見送った）。`workflow_ui_qwen_inpaint.json` に、用途の異なる3つの塗り替え経路が
1つのワークフローとして入っており、**Queueを押すと全部同時に実行される**
（同じマスクから3種類の結果が一度に出るので、見比べて良いものを採用すればよい）。

| 経路 | 出力ファイル名 | 向いている用途 |
|---|---|---|
| **生成（Generated）** | `scp_comic_inpaint_*` | 範囲に**新しい絵**を描かせたい場合（形がおかしい、別のポーズにしたい等） |
| **単色塗り（Flat Fill）** | `scp_comic_flatfill_*` | 無地の生地など、**色だけ**周りに合わせればよい場合。色は完全一致するが、模様は無地になる |
| **クローンスタンプ（Clone Stamp）** | `scp_comic_clonestamp_*` | 無地ではなく、**しわ・折り目などの質感**も含めて周りとなじませたい場合 |

生成モデル経由の「Generated」は、色をプロンプトに数値（RGB）で書いても、
denoiseを下げても、高速化LoRAを外して30stepにしても、その位置（例:
腰の高さ）に別の色味（ハイライト等）を描こうとする傾向が消えず、周囲との
色ズレが解消しないケースを確認している（モデル側の構造的な癖で、パラメータ
調整では直らない。denoiseを下げて「軽く整えるだけ」にしても同様にズレた）。
そのため無地部分の修正は次の2つを使い分ける:

- **色だけ合えばよい** → Flat Fill（数値指定なので完全一致するが、模様は付かない）
- **しわ等の質感も欲しい** → Clone Stamp（同じ服の別の場所を実際に複製するので、
  色も模様も本物。ただし継ぎ目が輪郭線の形と噛み合わずわずかに見えることがある。
  Feather Maskで境界をぼかして目立ちにくくしている）

### 使い方

1. ComfyUIの画面で `Workflow` → `Open`（またはキャンバスにファイルをドラッグ＆
   ドロップ）で `scripts/providers/comfyui/workflow_ui_qwen_inpaint.json` を開く
   （通常の生成用ワークフローと同じAPI形式のJSON。読み込めない場合は、
   このファイルのノード一覧・接続を見ながら手動で同じグラフを組んでもよい）
2. "Source Image"（LoadImageノード）で直したいコマのPNG
   （例: `output/scp-XXX/panels/panel_N.png` や `panels_temp/panel_N_vM.png`）
   をアップロードする
3. そのノードを右クリック→「Open in MaskEditor」で、塗り替えたい範囲を
   ブラシで白く塗ってマスクを作る（このマスクが3経路すべてで共有される）
4. **Flat Fillを使う場合**: "Flat Fill Color"（EmptyImageノード）の`color`を、
   周りの生地の色に合わせて設定する。ノードのカラースウォッチをクリックすれば
   カラーピッカーで直接選べる（数値で指定したい場合は`0xRRGGBB`形式の整数、
   例えば RGB (63,66,65) なら `0x3F4241` = `4145729`）
5. **Clone Stampを使う場合**: 画像編集ソフトやプレビューでピクセル座標を確認し、
   - "Texture Donor"（ImageCropノード）の`x`,`y`,`width`,`height`を、**同じ服の
     別の場所**（しわ・折り目がある部分）を切り取る範囲に設定する
   - "Place Donor At Defect"（ImageCompositeMaskedノード）の`x`,`y`を、**直したい
     範囲の左上**（MaskEditorで塗った範囲の左上あたり）に合わせる
   - 座標がズレていると継ぎ目の一部が塗り替わらず残ることがあるので、結果を見て
     ズレていたら座標を微調整して再実行する
6. **Generatedを使う場合**: "Positive Prompt" のテキストを、その範囲に**何を
   描いてほしいか**の短い説明に書き換える（画風はStyle LoRAが担うのでここには
   書かない）。既定はメインの生成と同じ高速化LoRA構成（`steps: 2` / `cfg: 1`）
7. Queueで実行する。どの経路も最終の「Composite」ノードがマスク範囲外の
   ピクセルを元画像のまま保つので、直したい部分だけが自然に置き換わる
8. 3つの出力（"Save Image (Generated)" / "(Flat Fill)" / "(Clone Stamp)"）を
   見比べて、良ければ `output/scp-XXX/panels/panel_N.png` として保存し直す

