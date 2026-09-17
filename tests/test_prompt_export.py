import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import generate_panels  # noqa: E402
from lib import config as cfglib  # noqa: E402


def _cfgs():
    return {
        "style": {
            "generation": {"provider": "external", "prompt_profile": "default"},
            "prompt": {
                "default": {
                    "style_prompt": "style",
                    "composition_rules": "composition",
                    "no_text_rules": "no text",
                }
            },
        },
        "layout": {
            "panel": {"width": 720, "height": 720},
            "caption": {"default_position": "alternate"},
            "caption_presets": {"top-left": {}, "top-right": {}},
        },
        "characters": {},
        "languages": {"languages": ["ja", "en"]},
    }


def _script():
    return {
        "id": "scp-test",
        "panels": [
            {"scene": "Wide shot panel one", "characters": [], "caption": {"ja": "一", "en": "one"}},
            {"scene": "Medium shot panel two", "characters": [], "caption": {"ja": "二", "en": "two"}},
            {"scene": "Close shot panel three", "characters": [], "caption": {"ja": "三", "en": "three"}},
            {"scene": "Final shot panel four", "characters": [], "caption": {"ja": "四", "en": "four"}},
        ],
    }


def test_export_prompts_can_export_single_panel(tmp_path, monkeypatch):
    monkeypatch.setattr(cfglib, "ROOT", str(tmp_path))
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(tmp_path / "output"))

    generate_panels.export_prompts(_script(), _cfgs(), panel=3)

    prompts_dir = tmp_path / "output" / "scp-test" / "prompts"
    assert not (prompts_dir / "panel_1.txt").exists()
    assert (prompts_dir / "panel_3.txt").exists()
    assert (prompts_dir / "panel_3_imagegen_request.txt").exists()
    assert "panel three" in (prompts_dir / "panel_3.txt").read_text(encoding="utf-8")
    request = (prompts_dir / "panel_3_imagegen_request.txt").read_text(encoding="utf-8")
    assert "Produce exactly one standalone illustration for panel 3" in request
    assert "single-panel regeneration" in request

    manifest = json.loads((prompts_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["partial_export"] is True
    assert [p["panel"] for p in manifest["panels"]] == [3]
    assert manifest["panels"][0]["imagegen_request_file"].endswith("panel_3_imagegen_request.txt")


def test_export_prompts_exports_all_panels_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfglib, "ROOT", str(tmp_path))
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(tmp_path / "output"))

    generate_panels.export_prompts(_script(), _cfgs())

    prompts_dir = tmp_path / "output" / "scp-test" / "prompts"
    assert (prompts_dir / "panel_1.txt").exists()
    assert (prompts_dir / "panel_1_imagegen_request.txt").exists()
    assert (prompts_dir / "panel_4.txt").exists()
    assert (prompts_dir / "panel_4_imagegen_request.txt").exists()
    manifest = json.loads((prompts_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["partial_export"] is False
    assert [p["panel"] for p in manifest["panels"]] == [1, 2, 3, 4]
