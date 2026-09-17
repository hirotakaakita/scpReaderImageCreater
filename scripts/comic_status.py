"""Show where a comic is in the production pipeline."""
import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import publish_check  # noqa: E402


def find_script(comic_id):
    for directory in (cfglib.QUEUE_DIR, cfglib.DONE_DIR):
        path = os.path.join(directory, f"{comic_id}.yaml")
        if os.path.exists(path):
            return path
    return None


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def image_size(path):
    if not os.path.exists(path):
        return None
    with Image.open(path) as image:
        return image.size


def status(comic_id):
    cfgs = cfglib.load_configs()
    required_langs = list(cfgs["languages"].get("languages") or [])
    expected_panel_size = (int(cfgs["layout"]["panel"]["width"]),
                           int(cfgs["layout"]["panel"]["height"]))
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id)
    prompts_dir = os.path.join(comic_dir, "prompts")
    panels_dir = os.path.join(comic_dir, "panels")
    meta = load_json(os.path.join(comic_dir, "meta.json")) or {}
    selected = load_json(os.path.join(panels_dir, "selected.json")) or {}

    script_path = find_script(comic_id)
    script = None
    validation = "MISSING"
    if script_path:
        try:
            script = cfglib.load_script(script_path)
            validation = "OK"
        except Exception as exc:
            validation = f"FAIL: {exc}"
    panel_count = len(script.get("panels") or []) if script else int(meta.get("panels") or 0)

    lines = [f"Comic status: {comic_id}", ""]
    lines += ["Script:", f"  path: {script_path or 'missing'}", f"  validation: {validation}",
              f"  panels: {panel_count or 'unknown'}", ""]

    lines.append("Prompts:")
    for idx in range(1, panel_count + 1):
        prompt = os.path.join(prompts_dir, f"panel_{idx}.txt")
        request = os.path.join(prompts_dir, f"panel_{idx}_imagegen_request.txt")
        lines.append(f"  panel {idx}: prompt={'yes' if os.path.exists(prompt) else 'no'}, "
                     f"imagegen_request={'yes' if os.path.exists(request) else 'no'}")
    if panel_count == 0:
        lines.append("  unknown until script/meta exists")
    lines.append("")

    lines.append("Accepted panels:")
    for idx in range(1, panel_count + 1):
        path = os.path.join(panels_dir, f"panel_{idx}.png")
        size = image_size(path)
        label = "missing" if size is None else f"{size[0]}x{size[1]}"
        ok = "OK" if size == expected_panel_size else "WARN"
        provider = (selected.get(str(idx)) or {}).get("provider", "unknown")
        lines.append(f"  panel {idx}: {ok if size else 'MISSING'} {label} provider={provider}")
    lines.append("")

    lines.append("Language renders:")
    missing_langs = []
    for lang in required_langs:
        path = os.path.join(comic_dir, f"{lang}.png")
        if os.path.exists(path):
            lines.append(f"  {lang}: yes")
        else:
            missing_langs.append(lang)
    if missing_langs:
        lines.append("  missing: " + ", ".join(missing_langs))
    lines.append("")

    lines.append("Meta/publish:")
    lines.append(f"  meta.json: {'yes' if meta else 'no'}")
    if meta:
        lines.append(f"  complete: {meta.get('complete')}")
        lines.append(f"  languages: {len(meta.get('languages') or [])}/{len(required_langs)}")
        if meta.get("overflow"):
            lines.append(f"  overflow: {meta.get('overflow')}")
        if meta.get("missing_font"):
            lines.append(f"  missing_font: {meta.get('missing_font')}")
    errors = publish_check.check(comic_id) if meta else ["meta.json missing"]
    lines.append("  publish_check: OK" if not errors else "  publish_check: BLOCKED")
    for error in errors:
        lines.append(f"    - {error}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id")
    args = ap.parse_args()
    print(status(args.comic_id))


if __name__ == "__main__":
    main()
