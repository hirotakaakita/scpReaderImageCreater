"""設定・台本の読み込みと共通パス。"""
import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(ROOT, "output")
QUEUE_DIR = os.path.join(ROOT, "comics", "queue")
DONE_DIR = os.path.join(ROOT, "comics", "done")


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
