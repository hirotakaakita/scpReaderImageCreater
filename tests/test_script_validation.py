import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from lib import config as cfglib  # noqa: E402


LANGS = ["ja", "en", "cs", "de", "es", "fr", "it", "ko", "pl", "pt", "th", "uk", "vi", "zh", "zh_Hant"]


def cfgs():
    return {
        "languages": {"languages": LANGS},
        "characters": {"researcher": {"description": "x"}},
        "layout": {"caption_presets": {"top-left": {}}, "bubble_presets": {"top": {}}},
    }


def valid_script():
    caption = {lang: "text" for lang in LANGS}
    return {"id": "scp-test", "panels": [
        {"scene": "Wide shot", "characters": ["researcher"], "caption": copy.deepcopy(caption)},
        {"scene": "Medium shot", "characters": [], "caption": copy.deepcopy(caption)},
        {"scene": "Close shot", "characters": [], "caption": copy.deepcopy(caption)},
        {"scene": "Final shot", "characters": [], "caption": copy.deepcopy(caption)},
    ]}


def add_description_sources(script):
    for panel in script["panels"]:
        panel["source"] = {
            "section": "Description",
            "quote": "source words",
            "url": "https://example.test/scp-test",
            "fetched_at": "2026-01-01T00:00:00Z",
        }
    return script


def test_valid_script_passes():
    assert cfglib.validate_script(valid_script(), cfgs=cfgs())["id"] == "scp-test"


def test_missing_language_fails():
    script = valid_script()
    del script["panels"][0]["caption"]["th"]
    with pytest.raises(ValueError, match="th"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_unknown_character_fails():
    script = valid_script()
    script["panels"][0]["characters"] = ["not-registered"]
    with pytest.raises(ValueError, match="unknown character"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_unknown_caption_position_fails():
    script = valid_script()
    script["panels"][0]["caption_position"] = "somewhere"
    with pytest.raises(ValueError, match="caption_position"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_source_description_is_allowed():
    script = valid_script()
    script["panels"][0]["source"] = {
        "section": "Description", "quote": "source words", "url": "https://example.test/scp-test"}
    cfglib.validate_script(script, cfgs=cfgs())


def test_strict_source_requires_every_panel_source():
    with pytest.raises(ValueError, match="strict-source"):
        cfglib.validate_script(valid_script(), cfgs=cfgs(), require_source=True)


def test_strict_source_passes_when_every_panel_has_source():
    cfglib.validate_script(add_description_sources(valid_script()), cfgs=cfgs(), require_source=True)


def test_containment_source_is_only_allowed_on_final_panel():
    script = valid_script()
    script["panels"][1]["source"] = {
        "section": "Special Containment Procedures", "quote": "procedure", "url": "https://example.test"}
    with pytest.raises(ValueError, match="final panel"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_containment_source_is_allowed_on_final_panel():
    script = valid_script()
    script["panels"][-1]["source"] = {
        "section": "Special Containment Procedures", "quote": "procedure", "url": "https://example.test"}
    cfglib.validate_script(script, cfgs=cfgs())
