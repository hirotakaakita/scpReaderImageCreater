"""Gemini（Nano Banana / Nano Banana Pro）で画像を生成するプロバイダ。

generate_panels.py から generate_image(prompt, ref_images, gen_cfg) が呼ばれる。
GEMINI_API_KEY 環境変数が必要（run_pipeline.py側でmock/export-prompts以外は必須チェック済み）。
設定は config/style.yaml の generation.gemini 以下（モデル名・画像サイズ・リトライ回数など）。
"""
import io
import os
import time

from PIL import Image


def generate_image(prompt, ref_images, gen_cfg):
    from google import genai

    cfg = gen_cfg.get("gemini", {})
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [prompt] + list(ref_images)
    image_config = {"aspect_ratio": gen_cfg.get("aspect_ratio", "1:1")}
    if cfg.get("image_size"):  # image_sizeはPro系のみ対応。null時は送らない
        image_config["image_size"] = cfg["image_size"]
    gen_config = {
        "response_modalities": ["TEXT", "IMAGE"],
        "image_config": image_config,
    }
    last_err = None
    for attempt in range(1, cfg.get("max_retries", 3) + 1):
        try:
            resp = client.models.generate_content(
                model=cfg["model"], contents=contents, config=gen_config)
            for cand in resp.candidates or []:
                for part in cand.content.parts or []:
                    data = getattr(part, "inline_data", None)
                    if data and data.data:
                        return Image.open(io.BytesIO(data.data))
            last_err = RuntimeError("no image in response")
        except Exception as e:  # レート制限・一時エラーを含む
            last_err = e
        wait = cfg.get("retry_wait_seconds", 20) * attempt
        print(f"  attempt {attempt} failed ({last_err}); retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"image generation failed: {last_err}")
