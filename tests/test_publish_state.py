import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_index  # noqa: E402
import publish_check  # noqa: E402
from lib import config as cfglib  # noqa: E402


def test_index_excludes_unknown_complete(tmp_path, monkeypatch):
    output = tmp_path / "output"
    comic = output / "scp-test"
    comic.mkdir(parents=True)
    (comic / "meta.json").write_text(json.dumps({"id": "scp-test"}), encoding="utf-8")
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(output))
    monkeypatch.setattr(cfglib, "ROOT", str(tmp_path))
    payload = build_index.build()
    assert payload["schemaVersion"] == 1
    assert payload["comics"] == []


def test_index_includes_only_explicit_complete(tmp_path, monkeypatch):
    output = tmp_path / "output"
    comic = output / "scp-test"
    comic.mkdir(parents=True)
    (comic / "meta.json").write_text(json.dumps({
        "id": "scp-test", "complete": True, "languages": [], "created_at": "2026-01-01T00:00:00Z"
    }), encoding="utf-8")
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(output))
    monkeypatch.setattr(cfglib, "ROOT", str(tmp_path))
    payload = build_index.build()
    assert [c["id"] for c in payload["comics"]] == ["scp-test"]


def test_publish_check_rejects_wrong_panel_size(tmp_path, monkeypatch):
    output = tmp_path / "output"
    comic = output / "scp-test"
    panels = comic / "panels"
    panels.mkdir(parents=True)
    Image.new("RGB", (800, 600)).save(panels / "panel_1.png")
    Image.new("RGB", (480, 480)).save(comic / "thumbnail.png")
    Image.new("RGB", (720, 720)).save(comic / "base.png")
    langs = ["ja"]
    Image.new("RGB", (720, 720)).save(comic / "ja.png")
    (comic / "meta.json").write_text(json.dumps({
        "id": "scp-test", "complete": True, "languages": langs, "panels": 1,
        "overflow": [], "missing_font": [], "attribution": {"source_url": "https://example.test"},
        "thumbnail_source": "panels/panel_1.png"
    }), encoding="utf-8")
    monkeypatch.setattr(cfglib, "OUTPUT_DIR", str(output))
    monkeypatch.setattr(cfglib, "load_configs", lambda: {
        "languages": {"languages": langs},
        "layout": {"panel": {"width": 720, "height": 720}, "thumbnail": {"size": 480}}
    })
    errors = publish_check.check("scp-test")
    assert any("expected 720x720" in error for error in errors)
