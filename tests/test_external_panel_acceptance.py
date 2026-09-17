import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import accept_external_panel  # noqa: E402
from lib import config as cfglib  # noqa: E402


def _patch_env(tmp_path, monkeypatch, panel_count=1):
    root = tmp_path
    queue = root / "comics" / "queue"
    done = root / "comics" / "done"
    output = root / "output"
    queue.mkdir(parents=True)
    done.mkdir(parents=True)
    panel_lines = []
    for i in range(1, panel_count + 1):
        panel_lines.extend([
            "  - scene: Wide shot of a test scene.\n",
            "    characters: []\n",
            "    caption:\n",
            f"      ja: テスト{i}\n",
            f"      en: Test {i}\n",
        ])
    (queue / "scp-test.yaml").write_text(
        "id: scp-test\n"
        "attribution:\n"
        "  source_url: https://example.test/scp-test\n"
        "panels:\n" + "".join(panel_lines),
        encoding="utf-8",
    )
    monkeypatch.setattr(cfglib, "ROOT", str(root))
    monkeypatch.setattr(cfglib, "QUEUE_DIR", str(queue))
    monkeypatch.setattr(cfglib, "DONE_DIR", str(done))
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(output))
    monkeypatch.setattr(cfglib, "load_configs", lambda: {
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
        "layout": {"panel": {"width": 720, "height": 720}, "caption": {}, "caption_presets": {}},
        "languages": {"languages": ["ja", "en"]},
        "characters": {},
    })
    return root, output


def test_accept_external_panel_normalizes_and_records_metadata(tmp_path, monkeypatch):
    root, output = _patch_env(tmp_path, monkeypatch, panel_count=1)
    source = root / "source.png"
    Image.new("RGB", (1600, 900), "white").save(source)

    accept_external_panel.accept_external_panel("scp-test", 1, str(source), provider="chatgpt-image")

    accepted = output / "scp-test" / "panels" / "panel_1.png"
    assert accepted.exists()
    with Image.open(accepted) as image:
        assert image.size == (720, 720)

    selected = json.loads((output / "scp-test" / "panels" / "selected.json").read_text(encoding="utf-8"))
    assert selected["1"]["provider"] == "chatgpt-image"
    assert selected["1"]["original_size"] == [1600, 900]
    assert selected["1"]["accepted_size"] == [720, 720]
    assert selected["1"]["normalization"] == "center_crop_and_resize"


def test_accept_many_imports_manifest_mapping(tmp_path, monkeypatch):
    root, output = _patch_env(tmp_path, monkeypatch, panel_count=2)
    src1 = root / "panel_1.png"
    src2 = root / "panel_2.png"
    Image.new("RGB", (1000, 1000), "white").save(src1)
    Image.new("RGB", (900, 1200), "white").save(src2)

    mapping = {1: {"source": str(src1)}, 2: {"source": str(src2), "note": "rerun"}}
    accept_external_panel.accept_many("scp-test", mapping, provider="imagegen")

    assert (output / "scp-test" / "panels" / "panel_1.png").exists()
    assert (output / "scp-test" / "panels" / "panel_2.png").exists()
    selected = json.loads((output / "scp-test" / "panels" / "selected.json").read_text(encoding="utf-8"))
    assert selected["1"]["provider"] == "imagegen"
    assert selected["2"]["note"] == "rerun"
