import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from lib import config as cfglib  # noqa: E402


def cfgs():
    langs = ["ja", "en"]
    return {
        "languages": {"languages": langs},
        "characters": {"researcher": {"description": "test"}},
        "layout": {
            "caption_presets": {"top-left": {}},
            "bubble_presets": {"top": {}},
        },
    }


def valid_script():
    return {
        "id": "scp-test",
        "local_characters": {"subject": {"description": "test"}},
        "panels": [{
            "scene": "Wide shot of researcher observing subject.",
            "characters": ["researcher", "subject"],
            "caption": {"ja": "説明", "en": "Description"},
            "caption_position": "top-left",
        }],
    }


def test_valid_script_passes():
    script = valid_script()
    assert cfglib.validate_script(script, cfgs=cfgs()) is script


def test_missing_language_fails():
    script = valid_script()
    del script["panels"][0]["caption"]["ja"]
    with pytest.raises(ValueError, match="missing/empty caption language"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_unknown_character_fails():
    script = valid_script()
    script["panels"][0]["characters"].append("invented")
    with pytest.raises(ValueError, match="unknown character"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_unknown_caption_position_fails():
    script = valid_script()
    script["panels"][0]["caption_position"] = "somewhere"
    with pytest.raises(ValueError, match="unknown caption_position"):
        cfglib.validate_script(script, cfgs=cfgs())


def test_partial_language_validation_can_be_requested():
    script = valid_script()
    del script["panels"][0]["caption"]["ja"]
    assert cfglib.validate_script(script, cfgs=cfgs(), require_all_languages=False) is script
