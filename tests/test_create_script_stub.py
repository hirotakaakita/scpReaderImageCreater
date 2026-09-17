import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import create_script_stub  # noqa: E402
from lib import config as cfglib  # noqa: E402


def test_create_script_stub_writes_full_language_skeleton(tmp_path, monkeypatch):
    queue = tmp_path / "comics" / "queue"
    monkeypatch.setattr(cfglib, "ROOT", str(tmp_path))
    monkeypatch.setattr(cfglib, "QUEUE_DIR", str(queue))
    monkeypatch.setattr(cfglib, "load_configs", lambda: {"languages": {"languages": ["ja", "en", "th"]}})

    result = create_script_stub.write_stub("SCP-TEST", panel_count=2)

    assert result["id"] == "scp-test"
    path = queue / "scp-test.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["id"] == "scp-test"
    assert list(data["title"].keys()) == ["ja", "en", "th"]
    assert len(data["panels"]) == 2
    assert data["panels"][0]["source"]["section"] == "Description"
    assert list(data["panels"][0]["caption"].keys()) == ["ja", "en", "th"]


def test_create_script_stub_refuses_overwrite_without_force(tmp_path, monkeypatch):
    queue = tmp_path / "comics" / "queue"
    queue.mkdir(parents=True)
    (queue / "scp-test.yaml").write_text("id: scp-test\n", encoding="utf-8")
    monkeypatch.setattr(cfglib, "QUEUE_DIR", str(queue))
    monkeypatch.setattr(cfglib, "load_configs", lambda: {"languages": {"languages": ["ja", "en"]}})

    with pytest.raises(FileExistsError):
        create_script_stub.write_stub("scp-test")
