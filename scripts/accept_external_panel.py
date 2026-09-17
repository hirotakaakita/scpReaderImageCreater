"""Import an externally generated image as an accepted panel.

The source image may be any dimensions/aspect ratio. The accepted panel is
center-cropped and resized to config/layout.yaml panel pixels, and selection
metadata is preserved in output/<id>/panels/selected.json.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import generate_panels  # noqa: E402


def find_script(comic_id):
    for directory in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
        path = os.path.join(directory, f"{comic_id}.yaml")
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"script not found for id: {comic_id}")


def _next_external_name(temp_dir, panel, ext):
    prefix = f"panel_{panel}_external_v"
    max_v = 0
    if os.path.isdir(temp_dir):
        for name in os.listdir(temp_dir):
            if name.startswith(prefix) and name.endswith(ext):
                num = name[len(prefix):-len(ext)]
                if num.isdigit():
                    max_v = max(max_v, int(num))
    return f"{prefix}{max_v + 1}{ext}"


def accept_external_panel(comic_id, panel, source_path, provider="external", note=None):
    if panel <= 0:
        raise ValueError("panel must be positive")
    if not os.path.exists(source_path):
        raise FileNotFoundError(source_path)

    cfgs = cfglib.load_configs()
    script = cfglib.load_script(find_script(comic_id))
    generate_panels._check_panel_index(script, panel)  # noqa: SLF001 - CLI helper reuse

    layout = cfgs["layout"]
    width = int(layout["panel"]["width"])
    height = int(layout["panel"]["height"])
    if width != height:
        raise ValueError(f"accepted panels must be square; layout is {width}x{height}")

    comic_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id)
    temp_dir = os.path.join(comic_dir, "panels_temp")
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(panels_dir, exist_ok=True)

    ext = os.path.splitext(source_path)[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    raw_name = _next_external_name(temp_dir, panel, ext)
    raw_path = os.path.join(temp_dir, raw_name)
    abs_source = os.path.abspath(source_path)
    if os.path.abspath(raw_path) != abs_source:
        shutil.copyfile(source_path, raw_path)

    dest = os.path.join(panels_dir, f"panel_{panel}.png")
    with Image.open(source_path) as image:
        original_size = list(image.size)
        accepted = ImageOps.fit(image.convert("RGB"), (width, height), method=Image.LANCZOS,
                                centering=(0.5, 0.5))
        accepted.save(dest)

    panel_data = script["panels"][panel - 1]
    prompt = generate_panels.build_prompt(
        script, panel_data, cfgs, generate_panels.prompt_profile(cfgs), panel_idx=panel - 1)
    entry = {
        "panel": panel,
        "provider": provider,
        "image": raw_name,
        "source_path": abs_source,
        "raw_path": os.path.relpath(raw_path, cfglib.ROOT),
        "accepted_path": os.path.relpath(dest, cfglib.ROOT),
        "scene": panel_data["scene"],
        "prompt": prompt,
        "seed": None,
        "mock": False,
        "original_size": original_size,
        "accepted_size": [width, height],
        "normalization": "center_crop_and_resize",
        "accepted_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if note:
        entry["note"] = note

    selected_path = os.path.join(panels_dir, "selected.json")
    selected = {}
    if os.path.exists(selected_path):
        with open(selected_path, encoding="utf-8") as f:
            selected = json.load(f)
    selected[str(panel)] = entry
    with open(selected_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    print(f"[accept] {source_path} -> {dest} ({width}x{height})")
    print(f"[accept] raw copy -> {raw_path}")
    print(f"[accept] metadata -> {selected_path}")
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, dest="comic_id")
    ap.add_argument("--panel", required=True, type=int)
    ap.add_argument("--source", required=True, help="externally generated image path")
    ap.add_argument("--provider", default="external", help="metadata label, e.g. chatgpt-image")
    ap.add_argument("--note")
    args = ap.parse_args()
    accept_external_panel(args.comic_id, args.panel, args.source,
                          provider=args.provider, note=args.note)


if __name__ == "__main__":
    main()
