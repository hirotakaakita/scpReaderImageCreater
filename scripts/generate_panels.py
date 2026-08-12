"""Nano Banana Pro (Gemini) で各コマの画像を生成する。

台本のscene + config/style.yaml(絵柄) + config/characters.yaml(キャラ定義)から
プロンプトを組み立て、output/<id>/panels/panel_N.png に保存する。
テキスト・吹き出しは一切描かせない（後工程のembed_text.pyが埋め込む）。

--mock を付けるとAPIを呼ばずプレースホルダー画像を生成する（レイアウト確認用）。
"""
import argparse
import io
import json
import os
import sys
import time

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402

# 吹き出しプリセット位置 → 空けておいてほしい場所の指示
_SPACE_HINTS = {
    "top": "the top area of the image",
    "top-left": "the upper-left area of the image",
    "top-right": "the upper-right area of the image",
    "bottom": "the bottom area of the image",
    "bottom-left": "the lower-left area of the image",
    "bottom-right": "the lower-right area of the image",
    "center": "the center of the image",
}


def build_prompt(script, panel, cfgs):
    style = cfgs["style"]
    characters = cfgs["characters"]
    parts = [style["style_prompt"].strip()]

    names = panel.get("characters") or []
    descs = []
    for key in names:
        if key in characters:
            descs.append(characters[key]["description"].strip())
    if descs:
        parts.append("Characters appearing in this panel (keep these designs exactly consistent):\n- "
                     + "\n- ".join(descs))

    parts.append("Scene: " + panel["scene"].strip())

    hints = []
    for bubble in panel.get("bubbles") or []:
        pos = bubble.get("position", "top")
        if isinstance(pos, str) and pos in _SPACE_HINTS:
            hints.append(_SPACE_HINTS[pos])
    if hints:
        parts.append("Leave calm, uncluttered empty space (plain background) in "
                     + " and ".join(dict.fromkeys(hints))
                     + " so a speech bubble can be overlaid there later.")

    parts.append(style["composition_rules"].strip())
    parts.append(style["no_text_rules"].strip())
    return "\n\n".join(parts)


def collect_reference_images(script, panel, cfgs, prev_panel_paths):
    """キャラクター参照画像 + 直前コマ画像をPIL Imageで返す。"""
    gen = cfgs["style"]["generation"]
    refs = []
    for key in panel.get("characters") or []:
        char = cfgs["characters"].get(key) or {}
        for rel in char.get("reference_images") or []:
            path = cfglib.rootpath(rel)
            if os.path.exists(path):
                refs.append(Image.open(path))
    if gen.get("use_previous_panels_as_reference") and prev_panel_paths:
        for path in prev_panel_paths[-2:]:  # 直前2コマまで
            refs.append(Image.open(path))
    return refs[: gen.get("max_reference_images", 6)]


def call_nano_banana(prompt, ref_images, gen_cfg):
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [prompt] + list(ref_images)
    image_config = {"aspect_ratio": gen_cfg.get("aspect_ratio", "1:1")}
    if gen_cfg.get("image_size"):  # image_sizeはPro系のみ対応。null時は送らない
        image_config["image_size"] = gen_cfg["image_size"]
    gen_config = {
        "response_modalities": ["TEXT", "IMAGE"],
        "image_config": image_config,
    }
    last_err = None
    for attempt in range(1, gen_cfg.get("max_retries", 3) + 1):
        try:
            resp = client.models.generate_content(
                model=gen_cfg["model"], contents=contents, config=gen_config)
            for cand in resp.candidates or []:
                for part in cand.content.parts or []:
                    data = getattr(part, "inline_data", None)
                    if data and data.data:
                        return Image.open(io.BytesIO(data.data))
            last_err = RuntimeError("no image in response")
        except Exception as e:  # レート制限・一時エラーを含む
            last_err = e
        wait = gen_cfg.get("retry_wait_seconds", 20) * attempt
        print(f"  attempt {attempt} failed ({last_err}); retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"image generation failed: {last_err}")


def make_mock_panel(index):
    img = Image.new("RGB", (1024, 1024), (225, 225, 228))
    d = ImageDraw.Draw(img)
    d.rectangle((20, 20, 1004, 1004), outline=(120, 120, 130), width=6)
    d.ellipse((362, 462, 662, 762), outline=(120, 120, 130), width=8)
    d.text((472, 180), f"PANEL {index}", fill=(90, 90, 100), font_size=60)
    return img


def generate(script, cfgs, mock=False):
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(panels_dir, exist_ok=True)

    gen_cfg = cfgs["style"]["generation"]
    prompts_log = []
    prev_paths = []
    for i, panel in enumerate(script["panels"], 1):
        out_path = os.path.join(panels_dir, f"panel_{i}.png")
        prompt = build_prompt(script, panel, cfgs)
        prompts_log.append({"panel": i, "prompt": prompt})
        print(f"[generate] panel {i}/{len(script['panels'])}")
        if mock:
            img = make_mock_panel(i)
        else:
            refs = collect_reference_images(script, panel, cfgs, prev_paths)
            img = call_nano_banana(prompt, refs, gen_cfg)
        img.convert("RGB").save(out_path)
        prev_paths.append(out_path)

    with open(os.path.join(panels_dir, "prompts.json"), "w", encoding="utf-8") as f:
        json.dump(prompts_log, f, ensure_ascii=False, indent=2)
    return comic_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    generate(script, cfgs, mock=args.mock)


if __name__ == "__main__":
    main()
