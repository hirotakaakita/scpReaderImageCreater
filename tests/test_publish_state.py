import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import run_pipeline  # noqa: E402


def test_process_does_not_publish_unknown_state(monkeypatch, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    script_path = queue / "scp-test.yaml"
    script_path.write_text("placeholder", encoding="utf-8")
    script = {"id": "scp-test", "panels": [{"scene": "x", "caption": {"en": "x"}}]}

    monkeypatch.setattr(run_pipeline.cfglib, "QUEUE_DIR", str(queue))
    monkeypatch.setattr(run_pipeline.cfglib, "load_script", lambda _: script)
    monkeypatch.setattr(run_pipeline.compose, "compose", lambda *_: None)
    monkeypatch.setattr(run_pipeline.embed_text, "embed", lambda *_, **__: {
        "complete": None, "overflow": [], "missing_font": []
    })
    published = []
    monkeypatch.setattr(run_pipeline, "move_to_done", lambda _: published.append("moved"))
    monkeypatch.setattr(run_pipeline.cfglib, "mark_used", lambda _: published.append("used"))

    run_pipeline.process(str(script_path), {}, skip_generate=True)
    assert published == []


def test_process_publishes_only_explicit_true(monkeypatch, tmp_path):
    queue = tmp_path / "queue"
    queue.mkdir()
    script_path = queue / "scp-test.yaml"
    script_path.write_text("placeholder", encoding="utf-8")
    script = {"id": "scp-test", "panels": [{"scene": "x", "caption": {"en": "x"}}]}

    monkeypatch.setattr(run_pipeline.cfglib, "QUEUE_DIR", str(queue))
    monkeypatch.setattr(run_pipeline.cfglib, "load_script", lambda _: script)
    monkeypatch.setattr(run_pipeline.compose, "compose", lambda *_: None)
    monkeypatch.setattr(run_pipeline.embed_text, "embed", lambda *_, **__: {
        "complete": True, "overflow": [], "missing_font": []
    })
    published = []
    monkeypatch.setattr(run_pipeline, "move_to_done", lambda _: published.append("moved"))
    monkeypatch.setattr(run_pipeline.cfglib, "mark_used", lambda _: published.append("used"))

    run_pipeline.process(str(script_path), {}, skip_generate=True)
    assert published == ["moved", "used"]
