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


@pytest.mark.parametrize("require_source", [False, True])
def test_addendum_requires_explicit_approval(require_source):
    script = add_description_sources(valid_script())
    script["panels"][-1]["source"]["section"] = "Addendum 107-2"
    with pytest.raises(ValueError, match="user-approved"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=require_source)


def test_user_approved_addendum_passes_strict_source():
    script = add_description_sources(valid_script())
    source = script["panels"][-1]["source"]
    source["section"] = "Addendum 107-2"
    source["exception"] = {"user_approved": True, "reason": "User approved this test example."}
    assert cfglib.validate_script(script, cfgs=cfgs(), require_source=True) is script


@pytest.mark.parametrize("exception", [
    None, True, {}, {"user_approved": True},
    {"user_approved": False, "reason": "Not approved"},
    {"user_approved": "true", "reason": "Not a boolean"},
    {"user_approved": 1, "reason": "Not a boolean"},
    {"user_approved": True, "reason": "  "},
    {"user_approved": True, "reason": 123},
])
def test_invalid_source_exception_fails(exception):
    script = add_description_sources(valid_script())
    script["panels"][-1]["source"].update(section="Addendum 107-2", exception=exception)
    with pytest.raises(ValueError, match="source.exception"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


def test_addendum_approval_does_not_apply_to_other_panels():
    script = add_description_sources(valid_script())
    script["panels"][-1]["source"].update(
        section="Addendum 107-2",
        exception={"user_approved": True, "reason": "Only this panel was approved."})
    script["panels"][1]["source"]["section"] = "Addendum 107-2"
    with pytest.raises(ValueError, match="panel 2:.*user-approved"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


@pytest.mark.parametrize("field", ["quote", "url"])
def test_addendum_approval_still_requires_provenance(field):
    script = add_description_sources(valid_script())
    source = script["panels"][-1]["source"]
    source.update(section="Addendum 107-2",
                  exception={"user_approved": True, "reason": "Approved example"})
    del source[field]
    with pytest.raises(ValueError, match=f"source.{field} is required"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


@pytest.mark.parametrize("section", ["Interview", "AddendumTypo", [], ""])
def test_exception_does_not_bypass_other_section_rules(section):
    script = add_description_sources(valid_script())
    script["panels"][0]["source"].update(
        section=section, exception={"user_approved": True, "reason": "Approved example"})
    with pytest.raises(ValueError):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


def test_addendum_approval_still_requires_all_languages():
    script = add_description_sources(valid_script())
    script["panels"][-1]["source"].update(
        section="Addendum 107-2", exception={"user_approved": True, "reason": "Approved example"})
    del script["panels"][-1]["caption"]["th"]
    with pytest.raises(ValueError, match="th"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


@pytest.mark.parametrize("require_source", [False, True])
def test_approved_containment_source_can_use_nonfinal_panel(require_source):
    script = add_description_sources(valid_script())
    script["panels"][1]["source"].update(
        section="Special Containment Procedures",
        exception={"user_approved": True, "reason": "User requested moving this content to panel 2."})
    assert cfglib.validate_script(script, cfgs=cfgs(), require_source=require_source) is script


@pytest.mark.parametrize("exception", [
    None, {}, {"user_approved": False, "reason": "Not approved"},
    {"user_approved": "true", "reason": "Not a boolean"},
    {"user_approved": True, "reason": " "},
])
def test_nonfinal_containment_requires_valid_approval(exception):
    script = add_description_sources(valid_script())
    script["panels"][1]["source"].update(
        section="Special Containment Procedures", exception=exception)
    with pytest.raises(ValueError, match="final panel"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


def test_containment_exception_is_panel_local():
    script = add_description_sources(valid_script())
    script["panels"][1]["source"].update(
        section="Special Containment Procedures",
        exception={"user_approved": True, "reason": "Only panel 2 is approved."})
    script["panels"][0]["source"]["section"] = "Special Containment Procedures"
    with pytest.raises(ValueError, match="panel 1:.*final panel"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)


@pytest.mark.parametrize("missing", ["quote", "url", "caption"])
def test_containment_exception_preserves_required_fields(missing):
    script = add_description_sources(valid_script())
    panel = script["panels"][1]
    panel["source"].update(
        section="Special Containment Procedures",
        exception={"user_approved": True, "reason": "Approved for panel 2."})
    if missing == "caption":
        del panel["caption"]["th"]
    else:
        del panel["source"][missing]
    with pytest.raises(ValueError, match="th" if missing == "caption" else f"source.{missing}"):
        cfglib.validate_script(script, cfgs=cfgs(), require_source=True)
