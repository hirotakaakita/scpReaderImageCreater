"""Create a YAML skeleton for a new SCP comic script.

This keeps the mechanical 15-language/source structure out of Codex output so
Codex only needs to fill source-backed content.
"""
import argparse
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from lib import config as cfglib  # noqa: E402

_ID_RE = re.compile(r"^scp-[A-Za-z0-9_-]+$")


def normalize_id(value):
    comic_id = value.strip().lower()
    if not comic_id.startswith("scp-"):
        comic_id = "scp-" + comic_id
    if not _ID_RE.match(comic_id):
        raise ValueError(f"invalid SCP comic id: {value!r}")
    return comic_id


def build_stub(comic_id, languages, panel_count=4):
    empty_langs = {lang: "" for lang in languages}
    panels = []
    for _ in range(panel_count):
        panels.append({
            "scene": "",
            "characters": [],
            "source": {
                "section": "Description",
                "quote": "",
                "url": "",
                "fetched_at": "",
            },
            "caption": dict(empty_langs),
        })
    return {
        "id": comic_id,
        "title": dict(empty_langs),
        "object_class": "",
        "attribution": {
            "article": comic_id.upper(),
            "source_url": "",
            "author": "",
        },
        "local_characters": {},
        "panels": panels,
    }


def write_stub(comic_id, panel_count=4, output_path=None, force=False):
    if panel_count <= 0:
        raise ValueError("panel_count must be positive")
    comic_id = normalize_id(comic_id)
    cfgs = cfglib.load_configs()
    languages = list(cfgs["languages"].get("languages") or [])
    if not languages:
        raise ValueError("config/languages.yaml has no languages")
    output_path = output_path or os.path.join(cfglib.QUEUE_DIR, f"{comic_id}.yaml")
    if os.path.exists(output_path) and not force:
        raise FileExistsError(f"script already exists: {output_path} (use --force to overwrite)")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    data = build_stub(comic_id, languages, panel_count=panel_count)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=120)
    return {
        "ok": True,
        "id": comic_id,
        "path": output_path,
        "panels": panel_count,
        "languages": languages,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id", help="SCP ID, e.g. scp-173 or 173")
    ap.add_argument("--panels", type=int, default=4)
    ap.add_argument("--output", help="override output YAML path")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", dest="json_output", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    result = write_stub(args.comic_id, panel_count=args.panels,
                        output_path=args.output, force=args.force)
    if args.json_output:
        serializable = dict(result)
        serializable["path"] = os.path.relpath(serializable["path"], cfglib.ROOT)
        print(json.dumps(serializable, ensure_ascii=False, indent=2))
    elif args.quiet:
        print(os.path.relpath(result["path"], cfglib.ROOT))
    else:
        print(f"[stub] created {os.path.relpath(result['path'], cfglib.ROOT)} "
              f"({result['panels']} panels, {len(result['languages'])} languages)")
        print("[stub] Fill scene/source/caption/title/attribution, then run strict validation.")


if __name__ == "__main__":
    main()
