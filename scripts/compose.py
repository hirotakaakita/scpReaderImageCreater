"""コマ画像を1枚の漫画（テキスト無しのbase.png）に合成する。"""
import argparse
import datetime
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
from lib import drawing  # noqa: E402


def build_footer_lines(script):
    at = script.get("attribution") or {}
    article = at.get("article", script["id"].upper())
    author = at.get("author")
    url = at.get("source_url", "")
    by = f'Based on "{article}"' + (f" by {author}" if author else "")
    return [
        f"{by} - SCP Foundation ({url})",
        "Original: CC BY-SA 3.0 / This comic: CC BY-SA 3.0 (creativecommons.org/licenses/by-sa/3.0)",
    ]


def compose(script, cfgs):
    layout = cfgs["layout"]
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    panels_dir = os.path.join(comic_dir, "panels")
    os.makedirs(comic_dir, exist_ok=True)

    n = len(script["panels"])
    panel_files = [os.path.join(panels_dir, f"panel_{i}.png") for i in range(1, n + 1)]
    for path in panel_files:
        if not os.path.exists(path):
            raise FileNotFoundError(path)

    pw, ph = layout["panel"]["width"], layout["panel"]["height"]
    strip = layout["strip"]
    cols = strip["columns"]
    if cols <= 0:
        raise ValueError("layout strip.columns must be positive")
    rows = math.ceil(n / cols)
    gutter, margin = strip["gutter"], strip["margin"]
    header_h = layout["header"]["height"]
    footer_h = layout["footer"]["height"]
    row_cell_h = [ph] * rows

    addendum_cfg = layout.get("addendum") or {}
    has_addendum = bool(script.get("addendum"))
    add_h = addendum_cfg.get("height", 0) if has_addendum else 0
    add_gap = addendum_cfg.get("gap", 0) if has_addendum else 0

    width = margin * 2 + cols * pw + (cols - 1) * gutter
    grid_h = sum(row_cell_h) + (rows - 1) * gutter
    height = (margin * 2 + header_h + gutter + grid_h
              + (add_gap + add_h if has_addendum else 0) + gutter + footer_h)

    img = Image.new("RGB", (width, height), strip["background"])
    draw = ImageDraw.Draw(img)
    header_rect = (margin, margin, width - margin, margin + header_h)
    grid_top = margin + header_h + gutter
    row_tops = []
    y = grid_top
    for r in range(rows):
        row_tops.append(y)
        y += row_cell_h[r] + gutter
    grid_bottom = y - gutter

    addendum_rect = None
    if has_addendum:
        addendum_rect = (margin, grid_bottom + add_gap, width - margin,
                         grid_bottom + add_gap + add_h)
        footer_top = addendum_rect[3] + gutter
    else:
        footer_top = grid_bottom + gutter
    footer_rect = (margin, footer_top, width - margin, footer_top + footer_h)

    rule_w = layout["header"].get("rule_width", 0)
    if rule_w:
        y = header_rect[3]
        draw.rectangle((margin, y - rule_w, width - margin, y), fill="#000000")

    panel_rects = []
    for i in range(n):
        col = i // rows
        row = i % rows
        if strip.get("column_order") == "rtl":
            col = cols - 1 - col
        x0 = margin + col * (pw + gutter)
        y0 = row_tops[row]
        rect = (x0, y0, x0 + pw, y0 + ph)
        panel_rects.append(rect)
        with Image.open(panel_files[i]) as source:
            panel = source.convert("RGB").resize((pw, ph), Image.LANCZOS)
        img.paste(panel, (x0, y0))

    if has_addendum:
        drawing.draw_caption_frame(draw, addendum_rect, addendum_cfg)

    frule = layout["footer"].get("rule_width", 0)
    if frule:
        y = footer_rect[1]
        draw.rectangle((margin, y, width - margin, y + frule), fill="#AAAAAA")

    base_path = os.path.join(comic_dir, "base.png")
    img.save(base_path)

    thumb_size = (layout.get("thumbnail") or {}).get("size", 480)
    thumb_path = os.path.join(comic_dir, "thumbnail.png")
    with Image.open(panel_files[0]) as source:
        thumb = source.convert("RGB").resize((thumb_size, thumb_size), Image.LANCZOS)
    thumb.save(thumb_path)
    print(f"[compose] {thumb_path} ({thumb_size}x{thumb_size}, panel 1)")

    # Re-composition changes the publication base. It must invalidate any previous
    # publish-complete state. Only a subsequent full-language embed may set True.
    meta = {
        "id": script["id"],
        "panels": n,
        "image_size": [width, height],
        "panel_rects": panel_rects,
        "addendum_rect": addendum_rect,
        "header_rect": header_rect,
        "footer_rect": footer_rect,
        "object_class": script.get("object_class"),
        "attribution": script.get("attribution") or {},
        "title": script.get("title") or {},
        "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "languages": [],
        "overflow": [],
        "missing_font": [],
        "complete": False,
    }
    with open(os.path.join(comic_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=True, indent=2)
    print(f"[compose] {base_path} ({width}x{height}, {n} panels)")
    return base_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script_path")
    args = ap.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(args.script_path)
    compose(script, cfgs)


if __name__ == "__main__":
    main()
