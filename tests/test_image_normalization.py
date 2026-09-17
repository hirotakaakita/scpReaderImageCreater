import os
import sys

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import compose  # noqa: E402


def test_normalize_panel_center_crops_to_exact_pixels():
    source = Image.new("RGB", (1600, 900), "white")
    result = compose.normalize_panel(source, 720, 720)
    assert result.size == (720, 720)


def test_normalize_panel_handles_portrait_input():
    source = Image.new("RGB", (800, 1400), "white")
    result = compose.normalize_panel(source, 720, 720)
    assert result.size == (720, 720)
