"""Build a disposable visual review sheet for a generated comic."""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def _load_thumb(path, max_size=(360, 360)):
    with Image.open(path) as image:
        return ImageOps.contain(image.convert("RGB"), max_size, method=Image.LANCZOS)


def _items(comic_id, langs):
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id)
    panels_dir = os.path.join(comic_dir, "panels")
    items = []
    idx = 1
    while True:
        path = os.path.join(panels_dir, f"panel_{idx}.png")
        if not os.path.exists(path):
            break
        items.append((f"panel {idx}", path))
        idx += 1
    for name in ("thumbnail.png", "base.png"):
        path = os.path.join(comic_dir, name)
        if os.path.exists(path):
            items.append((name, path))
    for lang in langs:
        path = os.path.join(comic_dir, f"{lang}.png")
        if os.path.exists(path):
            items.append((f"{lang}.png", path))
    return items


def build(comic_id, langs=None, out_path=None):
    langs = langs or ["ja", "en"]
    items = _items(comic_id, langs)
    if not items:
        raise FileNotFoundError(f"no generated images found for {comic_id}")

    padding = 24
    label_h = 28
    cell_w = 400
    cell_h = 420
    cols = 2
    rows = (len(items) + cols - 1) // cols
    width = padding + cols * cell_w + (cols - 1) * padding + padding
    height = padding + rows * cell_h + (rows - 1) * padding + padding
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    for index, (label, path) in enumerate(items):
        row, col = divmod(index, cols)
        x = padding + col * (cell_w + padding)
        y = padding + row * (cell_h + padding)
        draw.text((x, y), label, fill="black")
        try:
            thumb = _load_thumb(path, (cell_w, cell_h - label_h))
            px = x + (cell_w - thumb.width) // 2
            py = y + label_h + (cell_h - label_h - thumb.height) // 2
            canvas.paste(thumb, (px, py))
            draw.rectangle((x, y + label_h, x + cell_w, y + cell_h), outline="#CCCCCC", width=1)
        except Exception as exc:
            draw.text((x, y + label_h), f"failed to load: {exc}", fill="red")

    out_path = out_path or os.path.join(cfglib.OUTPUT_DIR, comic_id, "review-sheet.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)
    print(f"[review-sheet] {out_path}")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id")
    ap.add_argument("--langs", default="ja,en",
                    help="comma-separated language renders to include, default ja,en")
    ap.add_argument("--out")
    args = ap.parse_args()
    langs = [lang.strip() for lang in args.langs.split(",") if lang.strip()]
    build(args.comic_id, langs=langs, out_path=args.out)


if __name__ == "__main__":
    main()
