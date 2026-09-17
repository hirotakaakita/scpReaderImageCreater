"""Check whether a comic has every deterministic artifact required for publication."""
import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def check(comic_id):
    cfgs = cfglib.load_configs()
    required_langs = list(cfgs["languages"]["languages"])
    pw = int(cfgs["layout"]["panel"]["width"])
    ph = int(cfgs["layout"]["panel"]["height"])
    ts = int((cfgs["layout"].get("thumbnail") or {}).get("size", 480))
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id)
    errors = []

    meta_path = os.path.join(comic_dir, "meta.json")
    if not os.path.exists(meta_path):
        return ["meta.json missing"]
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    if meta.get("complete") is not True:
        errors.append("meta.complete is not true")
    if set(meta.get("languages") or []) != set(required_langs):
        errors.append("meta.languages does not match production language set")
    if meta.get("overflow"):
        errors.append("text overflow remains")
    if meta.get("missing_font"):
        errors.append("missing font remains")
    if not (meta.get("attribution") or {}).get("source_url"):
        errors.append("attribution.source_url missing")

    for lang in required_langs:
        if not os.path.exists(os.path.join(comic_dir, f"{lang}.png")):
            errors.append(f"{lang}.png missing")
    for filename in ("base.png", "thumbnail.png"):
        if not os.path.exists(os.path.join(comic_dir, filename)):
            errors.append(f"{filename} missing")

    panel_count = int(meta.get("panels") or 0)
    for idx in range(1, panel_count + 1):
        path = os.path.join(comic_dir, "panels", f"panel_{idx}.png")
        if not os.path.exists(path):
            errors.append(f"panels/panel_{idx}.png missing")
            continue
        with Image.open(path) as image:
            if image.size != (pw, ph):
                errors.append(f"panel_{idx}.png is {image.width}x{image.height}; expected {pw}x{ph}")

    thumb_path = os.path.join(comic_dir, "thumbnail.png")
    if os.path.exists(thumb_path):
        with Image.open(thumb_path) as image:
            if image.size != (ts, ts):
                errors.append(f"thumbnail.png is {image.width}x{image.height}; expected {ts}x{ts}")
    if meta.get("thumbnail_source") not in (None, "panels/panel_1.png"):
        errors.append("thumbnail source is not accepted panel_1.png")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id")
    args = ap.parse_args()
    errors = check(args.comic_id)
    if errors:
        print(f"[publish-check] FAIL {args.comic_id}")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"[publish-check] OK {args.comic_id}")


if __name__ == "__main__":
    main()
