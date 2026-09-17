import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import accept_external_panel  # noqa: E402
from lib import config as cfglib  # noqa: E402


def test_accept_external_panel_normalizes_and_records_metadata(tmp_path, monkeypatch):
    root = tmp_path
    queue = root / "comics" / "queue"
    done = root / "comics" / "done"
    output = root / "output"
    queue.mkdir(parents=True)
    done.mkdir(parents=True)

    script = {
        "id": "scp-test",
        "panels": [{
            "scene": "Wide shot of a test scene.",
            "characters": [],
            "caption": {"ja": "テスト", "en": "Test"},
        }],
        "attribution": {"source_url": "https://example.test/scp-test"},
    }
    (queue / "scp-test.yaml").write_text(
        "id: scp-test\n"
        "attribution:\n"
        "  source_url: https://example.test/scp-test\n"
        "panels:\n"
        "  - scene: Wide shot of a test scene.\n"
        "    characters: []\n"
        "    caption:\n"
        "      ja: テスト\n"
        "      en: Test\n",
        encoding="utf-8",
    )
    source = root / "source.png"
    Image.new("RGB", (1600, 900), "white").save(source)

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
