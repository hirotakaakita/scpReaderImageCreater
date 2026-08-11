"""設定・台本の読み込みと共通パス。"""
import datetime
import json
import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(ROOT, "output")
QUEUE_DIR = os.path.join(ROOT, "comics", "queue")
DONE_DIR = os.path.join(ROOT, "comics", "done")
USED_PATH = os.path.join(ROOT, "state", "used.json")


def rootpath(*parts):
    return os.path.join(ROOT, *parts)


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_configs():
    """config/ 以下の全設定をまとめて読む。"""
    return {
        "style": load_yaml(rootpath("config", "style.yaml")),
        "layout": load_yaml(rootpath("config", "layout.yaml")),
        "characters": load_yaml(rootpath("config", "characters.yaml")).get("characters", {}),
        "languages": load_yaml(rootpath("config", "languages.yaml")),
    }


def load_script(path):
    script = load_yaml(path)
    if not script.get("id"):
        raise ValueError(f"script has no id: {path}")
    if not script.get("panels"):
        raise ValueError(f"script has no panels: {path}")
    return script


def font_path_for(lang, lang_cfg):
    fonts = lang_cfg["fonts"]
    rel = fonts.get("by_language", {}).get(lang, fonts["default"])
    return rootpath(rel)


def is_char_wrap(lang, lang_cfg):
    return lang in (lang_cfg.get("char_wrap") or [])


def load_used():
    """漫画を生成済みのSCPの記録（state/used.json）。消すと重複生成の恐れがある。"""
    if not os.path.exists(USED_PATH):
        return {}
    with open(USED_PATH, encoding="utf-8") as f:
        return json.load(f)


def mark_used(comic_id):
    used = load_used()
    if comic_id not in used:
        used[comic_id] = {
            "generatedAt": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    os.makedirs(os.path.dirname(USED_PATH), exist_ok=True)
    with open(USED_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(used.items())), f, ensure_ascii=True, indent=2)
    return used
