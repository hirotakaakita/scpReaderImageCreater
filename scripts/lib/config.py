"""設定・台本の読み込み、検証、共通パス。"""
import datetime
import json
import os
import re

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(ROOT, "output")
QUEUE_DIR = os.path.join(ROOT, "comics", "queue")
DONE_DIR = os.path.join(ROOT, "comics", "done")
USED_PATH = os.path.join(ROOT, "state", "used.json")
_ID_RE = re.compile(r"^scp-[A-Za-z0-9_-]+$")
_SOURCE_SECTIONS = {"Description", "Special Containment Procedures"}


def rootpath(*parts):
    return os.path.join(ROOT, *parts)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"empty YAML: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"top-level YAML must be a mapping: {path}")
    return data


def load_configs():
    return {
        "style": load_yaml(rootpath("config", "style.yaml")),
        "layout": load_yaml(rootpath("config", "layout.yaml")),
        "characters": load_yaml(rootpath("config", "characters.yaml")).get("characters", {}),
        "languages": load_yaml(rootpath("config", "languages.yaml")),
    }


def validate_script(script, path=None, cfgs=None, require_all_languages=True):
    where = path or script.get("id") or "<script>"
    errors = []
    comic_id = script.get("id")
    if not isinstance(comic_id, str) or not comic_id.strip():
        errors.append("id is required and must be a string")
    elif not _ID_RE.match(comic_id):
        errors.append(f"invalid id format: {comic_id!r}")
    if path and comic_id:
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem != comic_id and not stem.startswith(f"{comic_id}-dup"):
            errors.append(f"id {comic_id!r} does not match filename {stem!r}")

    panels = script.get("panels")
    if not isinstance(panels, list) or not panels:
        errors.append("panels is required and must be a non-empty list")
        panels = []

    cfgs = cfgs or load_configs()
    required_langs = list(cfgs["languages"].get("languages") or [])
    global_chars = cfgs.get("characters") or {}
    local_chars = script.get("local_characters") or {}
    if not isinstance(local_chars, dict):
        errors.append("local_characters must be a mapping")
        local_chars = {}
    known_chars = set(global_chars) | set(local_chars)
    caption_presets = set((cfgs["layout"].get("caption_presets") or {}).keys())
    bubble_presets = set((cfgs["layout"].get("bubble_presets") or {}).keys())

    for idx, panel in enumerate(panels, 1):
        prefix = f"panel {idx}"
        if not isinstance(panel, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue
        scene = panel.get("scene")
        if not isinstance(scene, str) or not scene.strip():
            errors.append(f"{prefix}: scene is required")
        chars = panel.get("characters") or []
        if not isinstance(chars, list):
            errors.append(f"{prefix}: characters must be a list")
        else:
            unknown = [key for key in chars if key not in known_chars]
            if unknown:
                errors.append(f"{prefix}: unknown character key(s): {', '.join(map(str, unknown))}")

        caption = panel.get("caption")
        if not isinstance(caption, dict) or not caption:
            errors.append(f"{prefix}: caption is required and must be a language mapping")
        elif require_all_languages:
            missing = [lang for lang in required_langs
                       if not isinstance(caption.get(lang), str) or not caption[lang].strip()]
            if missing:
                errors.append(f"{prefix}: missing/empty caption language(s): {', '.join(missing)}")

        source = panel.get("source")
        if source is not None:
            if not isinstance(source, dict):
                errors.append(f"{prefix}: source must be a mapping")
            else:
                section = source.get("section")
                if section not in _SOURCE_SECTIONS:
                    errors.append(f"{prefix}: source.section must be Description or Special Containment Procedures")
                if section == "Special Containment Procedures" and idx != len(panels):
                    errors.append(f"{prefix}: Special Containment Procedures may only be used in the final panel")
                for key in ("quote", "url"):
                    if not isinstance(source.get(key), str) or not source[key].strip():
                        errors.append(f"{prefix}: source.{key} is required when source is present")

        pos = panel.get("caption_position")
        if isinstance(pos, str) and pos not in caption_presets:
            errors.append(f"{prefix}: unknown caption_position {pos!r}")
        elif pos is not None and not isinstance(pos, (str, dict)):
            errors.append(f"{prefix}: caption_position must be a preset name or coordinate mapping")

        for bidx, bubble in enumerate(panel.get("bubbles") or [], 1):
            if not isinstance(bubble, dict):
                errors.append(f"{prefix} bubble {bidx}: must be a mapping")
                continue
            bpos = bubble.get("position", "top")
            if isinstance(bpos, str) and bpos not in bubble_presets:
                errors.append(f"{prefix} bubble {bidx}: unknown position {bpos!r}")

    addendum = script.get("addendum")
    if addendum is not None and not isinstance(addendum, dict):
        errors.append("addendum must be a language mapping")
    elif isinstance(addendum, dict) and require_all_languages:
        missing = [lang for lang in required_langs
                   if not isinstance(addendum.get(lang), str) or not addendum[lang].strip()]
        if missing:
            errors.append(f"addendum missing/empty language(s): {', '.join(missing)}")

    if errors:
        raise ValueError(f"invalid comic script {where}:\n- " + "\n- ".join(errors))
    return script


def load_script(path, require_all_languages=True):
    script = load_yaml(path)
    return validate_script(script, path=path, require_all_languages=require_all_languages)


def font_path_for(lang, lang_cfg):
    fonts = lang_cfg["fonts"]
    rel = fonts.get("by_language", {}).get(lang, fonts["default"])
    return rootpath(rel)


def is_char_wrap(lang, lang_cfg):
    return lang in (lang_cfg.get("char_wrap") or [])


def load_used():
    if not os.path.exists(USED_PATH):
        return {}
    with open(USED_PATH, encoding="utf-8") as f:
        return json.load(f)


def mark_used(comic_id):
    used = load_used()
    if comic_id not in used:
        used[comic_id] = {"generatedAt": datetime.datetime.now(datetime.timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ")}
    os.makedirs(os.path.dirname(USED_PATH), exist_ok=True)
    with open(USED_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(used.items())), f, ensure_ascii=True, indent=2)
    return used
