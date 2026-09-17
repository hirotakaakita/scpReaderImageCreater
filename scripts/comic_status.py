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
        return list(image.size)


def status_data(comic_id):
    cfgs = cfglib.load_configs()
    required_langs = list(cfgs["languages"].get("languages") or [])
    expected_panel_size = [int(cfgs["layout"]["panel"]["width"]),
                           int(cfgs["layout"]["panel"]["height"])]
    comic_dir = os.path.join(cfglib.OUTPUT_DIR, comic_id)
    prompts_dir = os.path.join(comic_dir, "prompts")
    panels_dir = os.path.join(comic_dir, "panels")
    meta = load_json(os.path.join(comic_dir, "meta.json")) or {}
    selected = load_json(os.path.join(panels_dir, "selected.json")) or {}

    script_path = find_script(comic_id)
    script = None
    validation = {"ok": False, "error": "script missing"}
    if script_path:
        try:
            script = cfglib.load_script(script_path)
            validation = {"ok": True, "error": None}
        except Exception as exc:
            validation = {"ok": False, "error": str(exc)}
    panel_count = len(script.get("panels") or []) if script else int(meta.get("panels") or 0)

    prompts = []
    accepted_panels = []
    for idx in range(1, panel_count + 1):
        prompt_path = os.path.join(prompts_dir, f"panel_{idx}.txt")
        request_path = os.path.join(prompts_dir, f"panel_{idx}_imagegen_request.txt")
        prompts.append({
            "panel": idx,
            "prompt": os.path.exists(prompt_path),
            "imagegenRequest": os.path.exists(request_path),
            "promptPath": os.path.relpath(prompt_path, cfglib.ROOT) if os.path.exists(prompt_path) else None,
            "imagegenRequestPath": os.path.relpath(request_path, cfglib.ROOT) if os.path.exists(request_path) else None,
        })

        path = os.path.join(panels_dir, f"panel_{idx}.png")
        size = image_size(path)
        accepted_panels.append({
            "panel": idx,
            "exists": size is not None,
            "size": size,
            "ok": size == expected_panel_size,
            "provider": (selected.get(str(idx)) or {}).get("provider"),
            "path": os.path.relpath(path, cfglib.ROOT) if size else None,
        })

    language_renders = {}
    missing_langs = []
    for lang in required_langs:
        exists = os.path.exists(os.path.join(comic_dir, f"{lang}.png"))
        language_renders[lang] = exists
        if not exists:
            missing_langs.append(lang)

    publish_errors = publish_check.check(comic_id) if meta else ["meta.json missing"]
    data = {
        "id": comic_id,
        "script": {
            "path": os.path.relpath(script_path, cfglib.ROOT) if script_path else None,
            "validation": validation,
            "panels": panel_count or None,
        },
        "prompts": prompts,
        "acceptedPanels": accepted_panels,
        "languageRenders": language_renders,
        "missingLanguages": missing_langs,
        "meta": {
            "exists": bool(meta),
            "complete": meta.get("complete") if meta else None,
            "languages": meta.get("languages") if meta else [],
            "overflow": meta.get("overflow") if meta else [],
            "missingFont": meta.get("missing_font") if meta else [],
        },
        "publish": {
            "ok": not publish_errors,
            "errors": publish_errors,
        },
    }
    data["nextActions"] = next_actions(data)
    return data


def next_actions(data):
    if not data["script"]["path"]:
        return ["create script with $make-scp-comic-script or scripts/create_script_stub.py"]
    if not data["script"]["validation"]["ok"]:
        return ["fix YAML validation errors"]
    missing_requests = [str(p["panel"]) for p in data["prompts"] if not p["imagegenRequest"]]
    if missing_requests:
        return ["export imagegen request prompts for panel(s): " + ", ".join(missing_requests)]
    missing_panels = [str(p["panel"]) for p in data["acceptedPanels"] if not p["exists"]]
    bad_size = [str(p["panel"]) for p in data["acceptedPanels"] if p["exists"] and not p["ok"]]
    if missing_panels:
        return ["generate/import accepted panel(s): " + ", ".join(missing_panels)]
    if bad_size:
        return ["re-accept panel(s) to normalize size: " + ", ".join(bad_size)]
    if data["missingLanguages"] or not data["meta"]["exists"]:
        return ["run python scripts/run_pipeline.py --id <id> --skip-generate"]
    if not data["publish"]["ok"]:
        return ["fix publish_check errors"]
    return ["publish-ready"]


def format_text(data, quiet=False):
    if quiet:
        status = "OK" if data["publish"]["ok"] else "BLOCKED"
        return f"{data['id']}: {status}; next: {data['nextActions'][0]}"

    lines = [f"Comic status: {data['id']}", ""]
    lines += ["Script:", f"  path: {data['script']['path'] or 'missing'}",
              f"  validation: {'OK' if data['script']['validation']['ok'] else 'FAIL'}",
              f"  panels: {data['script']['panels'] or 'unknown'}"]
    if data["script"]["validation"]["error"]:
        lines.append(f"  error: {data['script']['validation']['error']}")
    lines.append("")

    lines.append("Prompts:")
    if data["prompts"]:
        for item in data["prompts"]:
            lines.append(f"  panel {item['panel']}: prompt={'yes' if item['prompt'] else 'no'}, "
                         f"imagegen_request={'yes' if item['imagegenRequest'] else 'no'}")
    else:
        lines.append("  unknown until script/meta exists")
    lines.append("")

    lines.append("Accepted panels:")
    for item in data["acceptedPanels"]:
        if not item["exists"]:
            lines.append(f"  panel {item['panel']}: MISSING")
        else:
            size = item["size"]
            label = f"{size[0]}x{size[1]}"
            lines.append(f"  panel {item['panel']}: {'OK' if item['ok'] else 'WARN'} {label} "
                         f"provider={item['provider'] or 'unknown'}")
    lines.append("")

    lines.append("Language renders:")
    present = [lang for lang, ok in data["languageRenders"].items() if ok]
    lines.append(f"  present: {len(present)}/{len(data['languageRenders'])}")
    if data["missingLanguages"]:
        lines.append("  missing: " + ", ".join(data["missingLanguages"]))
    lines.append("")

    lines.append("Meta/publish:")
    lines.append(f"  meta.json: {'yes' if data['meta']['exists'] else 'no'}")
    lines.append(f"  complete: {data['meta']['complete']}")
    lines.append("  publish_check: OK" if data["publish"]["ok"] else "  publish_check: BLOCKED")
    for error in data["publish"]["errors"]:
        lines.append(f"    - {error}")
    lines.append("")
    lines.append("Next:")
    for action in data["nextActions"]:
        lines.append(f"  - {action}")
    return "\n".join(lines)


def status(comic_id):
    """Backward-compatible text status."""
    return format_text(status_data(comic_id))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id")
    ap.add_argument("--json", dest="json_output", action="store_true",
                    help="print compact machine-readable result")
    ap.add_argument("--quiet", action="store_true",
                    help="print a one-line summary")
    args = ap.parse_args()
    data = status_data(args.comic_id)
    if args.json_output:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_text(data, quiet=args.quiet))


if __name__ == "__main__":
    main()
