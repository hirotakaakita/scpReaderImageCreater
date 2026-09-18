"""台本・パネル・完成出力を機械的に検査する。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402
import export_chatgpt_prompts as prompts  # noqa: E402


def find_script(comic_id):
    for directory in (cfglib.DONE_DIR, cfglib.QUEUE_DIR):
        path = os.path.join(directory, f"{comic_id}.yaml")
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(f"script not found for id: {comic_id}")


def validate_script(script, cfgs):
    errors = []
    languages = cfgs["languages"]["languages"]
    for index, panel in enumerate(script["panels"], 1):
        if not panel.get("scene", "").strip():
            errors.append(f"panel {index}: scene is missing")
        for key in panel.get("characters") or []:
            if not prompts.lookup_character(key, script, cfgs):
                errors.append(f"panel {index}: unknown character {key}")
        caption = panel.get("caption") or {}
        missing = [lang for lang in languages if not caption.get(lang, "").strip()]
        if missing:
            errors.append(f"panel {index}: missing caption languages: {', '.join(missing)}")
    return errors


def validate_panels(script):
    directory = os.path.join(cfglib.OUTPUT_DIR, script["id"], "panels")
    return [f"missing panel_{index}.png" for index in range(1, len(script["panels"]) + 1)
            if not os.path.isfile(os.path.join(directory, f"panel_{index}.png"))]


def validate_output(script, cfgs):
    directory = os.path.join(cfglib.OUTPUT_DIR, script["id"])
    errors = validate_panels(script)
    meta_path = os.path.join(directory, "meta.json")
    if not os.path.isfile(meta_path):
        return errors + ["missing meta.json"]
    with open(meta_path, encoding="utf-8") as handle:
        meta = json.load(handle)
    if meta.get("complete") is not True:
        errors.append(f"output is incomplete (overflow={meta.get('overflow')}, missing_font={meta.get('missing_font')})")
    for lang in cfgs["languages"]["languages"]:
        if not os.path.isfile(os.path.join(directory, f"{lang}.png")):
            errors.append(f"missing {lang}.png")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--stage", choices=("script", "panels", "output"), default="script")
    args = parser.parse_args()
    cfgs = cfglib.load_configs()
    script = cfglib.load_script(find_script(args.id))
    checks = {"script": validate_script(script, cfgs), "panels": validate_panels(script),
              "output": validate_output(script, cfgs)}
    errors = checks[args.stage]
    if errors:
        for error in errors:
            print(f"[validate] ERROR: {error}")
        raise SystemExit(1)
    print(f"[validate] {script['id']} {args.stage}: OK")


if __name__ == "__main__":
    main()
