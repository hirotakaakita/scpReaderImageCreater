"""Select a generated variant as the accepted panel and preserve its metadata."""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, dest="comic_id")
    ap.add_argument("--panel", required=True, type=int)
    ap.add_argument("--variant", required=True, type=int)
    args = ap.parse_args()
    if args.panel <= 0 or args.variant <= 0:
        ap.error("--panel and --variant must be positive")

    comic_dir = os.path.join(cfglib.OUTPUT_DIR, args.comic_id)
    temp_dir = os.path.join(comic_dir, "panels_temp")
    panels_dir = os.path.join(comic_dir, "panels")
    image_name = f"panel_{args.panel}_v{args.variant}.png"
    source = os.path.join(temp_dir, image_name)
    if not os.path.exists(source):
        raise FileNotFoundError(source)

    selected_meta = None
    log_path = os.path.join(temp_dir, "candidates.jsonl")
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("image") == image_name:
                    selected_meta = entry
    if selected_meta is None:
        raise ValueError(f"generation metadata not found for {image_name}; refusing untraceable selection")
    if selected_meta.get("mock"):
        raise ValueError(f"refusing to select mock candidate: {image_name}")

    os.makedirs(panels_dir, exist_ok=True)
    dest = os.path.join(panels_dir, f"panel_{args.panel}.png")
    shutil.copy2(source, dest)

    selected_path = os.path.join(panels_dir, "selected.json")
    selected = {}
    if os.path.exists(selected_path):
        with open(selected_path, encoding="utf-8") as f:
            selected = json.load(f)
    selected[str(args.panel)] = selected_meta
    with open(selected_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)
    print(f"[select] {source} -> {dest}")
    print(f"[select] metadata -> {selected_path}")


if __name__ == "__main__":
    main()
