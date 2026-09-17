"""Import externally generated images as accepted panels.

Each source image may be any dimensions/aspect ratio. The accepted panel is
center-cropped and resized to config/layout.yaml panel pixels, and selection
metadata is preserved in output/<id>/panels/selected.json.

Supported input modes:
- --panel N --source image.png for one panel
- --source-dir directory containing panel_1.png ... panel_N.png
- --manifest mapping.json for explicit panel -> image mapping
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

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


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


def _load_selected(selected_path):
    if not os.path.exists(selected_path):
        return {}
    with open(selected_path, encoding="utf-8") as f:
        return json.load(f)


def _save_selected(selected_path, selected):
    with open(selected_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)


def _normalized_ext(path):
    ext = os.path.splitext(path)[1].lower() or ".png"
    return ext if ext in _IMAGE_EXTS else ".png"


def accept_external_panel(comic_id, panel, source_path, provider="external", note=None,
                          cfgs=None, script=None, selected=None):
    if panel <= 0:
        raise ValueError("panel must be positive")
    if not os.path.exists(source_path):
        raise FileNotFoundError(source_path)

    cfgs = cfgs or cfglib.load_configs()
    script = script or cfglib.load_script(find_script(comic_id))
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

    ext = _normalized_ext(source_path)
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
    selected = selected if selected is not None else _load_selected(selected_path)
    selected[str(panel)] = entry
    _save_selected(selected_path, selected)

    print(f"[accept] {source_path} -> {dest} ({width}x{height})")
    print(f"[accept] raw copy -> {raw_path}")
    print(f"[accept] metadata -> {selected_path}")
    return entry


def _parse_panel_number(value):
    try:
        panel = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid panel number: {value!r}") from exc
    if panel <= 0:
        raise ValueError(f"panel number must be positive: {panel}")
    return panel


def _load_input_manifest(path):
    """Return {panel: {source, note?}} from a JSON manifest.

    Supported shapes:
    {"1": "./panel_1.png", "2": {"source": "./panel_2.png", "note": "..."}}
    {"panels": [{"panel": 1, "source": "./panel_1.png"}]}
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("panels") if isinstance(data, dict) and "panels" in data else data
    result = {}
    if isinstance(entries, dict):
        for key, value in entries.items():
            panel = _parse_panel_number(key)
            if isinstance(value, str):
                result[panel] = {"source": value}
            elif isinstance(value, dict) and value.get("source"):
                result[panel] = {"source": value["source"], "note": value.get("note")}
            else:
                raise ValueError(f"invalid manifest entry for panel {key!r}")
    elif isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict) or "panel" not in item or "source" not in item:
                raise ValueError("manifest panels must contain panel and source")
            result[_parse_panel_number(item["panel"])] = {
                "source": item["source"],
                "note": item.get("note"),
            }
    else:
        raise ValueError("manifest must be a mapping or a list under 'panels'")
    return result


def _source_dir_mapping(source_dir, script):
    """Find panel_N images in a directory without guessing ambiguous files."""
    result = {}
    for panel in range(1, len(script["panels"]) + 1):
        exact = [os.path.join(source_dir, f"panel_{panel}{ext}") for ext in _IMAGE_EXTS]
        exact = [p for p in exact if os.path.exists(p)]
        if exact:
            result[panel] = {"source": exact[0]}
            continue

        prefix = f"panel_{panel}_"
        candidates = []
        if os.path.isdir(source_dir):
            for name in os.listdir(source_dir):
                if name.startswith(prefix) and os.path.splitext(name)[1].lower() in _IMAGE_EXTS:
                    candidates.append(os.path.join(source_dir, name))
        candidates = sorted(candidates)
        if len(candidates) == 1:
            result[panel] = {"source": candidates[0]}
        elif len(candidates) > 1:
            raise ValueError(
                f"ambiguous source files for panel {panel}: "
                + ", ".join(os.path.basename(p) for p in candidates)
                + ". Rename the chosen file to panel_{panel}.png or use --manifest.")
    return result


def _mapping_from_args(args, script):
    modes = sum(bool(v) for v in (args.source, args.source_dir, args.manifest))
    if modes != 1:
        raise ValueError("provide exactly one of --source, --source-dir, or --manifest")
    if args.source:
        if args.panel is None:
            raise ValueError("--panel is required with --source")
        return {args.panel: {"source": args.source, "note": args.note}}
    if args.source_dir:
        if args.panel is not None:
            raise ValueError("--panel cannot be combined with --source-dir; use --source for one panel")
        return _source_dir_mapping(args.source_dir, script)
    manifest = _load_input_manifest(args.manifest)
    if args.note:
        for item in manifest.values():
            item.setdefault("note", args.note)
    return manifest


def accept_many(comic_id, mapping, provider="external", cfgs=None, script=None):
    cfgs = cfgs or cfglib.load_configs()
    script = script or cfglib.load_script(find_script(comic_id))
    panels_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id, "panels")
    os.makedirs(panels_dir, exist_ok=True)
    selected_path = os.path.join(panels_dir, "selected.json")
    selected = _load_selected(selected_path)
    entries = []
    for panel in sorted(mapping):
        generate_panels._check_panel_index(script, panel)  # noqa: SLF001
        item = mapping[panel]
        entries.append(accept_external_panel(
            comic_id, panel, item["source"], provider=provider,
            note=item.get("note"), cfgs=cfgs, script=script, selected=selected))
        selected = _load_selected(selected_path)
    print(f"[accept] imported {len(entries)} panel(s) for {comic_id}")
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, dest="comic_id")
    ap.add_argument("--panel", type=int, help="one-based panel number for --source mode")
    ap.add_argument("--source", help="one externally generated image path")
    ap.add_argument("--source-dir", help="directory containing panel_1.png ... panel_N.png")
    ap.add_argument("--manifest", help="JSON panel-to-source mapping")
    ap.add_argument("--provider", default="external", help="metadata label, e.g. imagegen")
    ap.add_argument("--note")
    args = ap.parse_args()

    cfgs = cfglib.load_configs()
    script = cfglib.load_script(find_script(args.comic_id))
    mapping = _mapping_from_args(args, script)
    if not mapping:
        raise ValueError("no panel images found to import")
    accept_many(args.comic_id, mapping, provider=args.provider, cfgs=cfgs, script=script)


if __name__ == "__main__":
    main()
