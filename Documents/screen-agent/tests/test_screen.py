"""Tests for screen capture — image must be small enough for Anthropic API.

Called by: pytest from the project root.
No existing test file for screen.py found.
User instruction: "try to fix whats wrong with the capture"
"""

import sys, os
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Clear any stubs set by test_agent_dispatch.py so we get the real modules.
for _stub in ('screen', 'mss', 'PIL', 'PIL.Image'):
    sys.modules.pop(_stub, None)

pytest.importorskip('mss', reason='mss not installed — install requirements.txt')

import io
from PIL import Image
import screen


API_SIZE_LIMIT = 1.5 * 1024 * 1024
MAX_LONG_EDGE  = 1280


def test_capture_returns_three_values():
    result = screen.capture()
    assert len(result) == 3


def test_capture_bytes_under_api_limit():
    img_bytes, _, _ = screen.capture()
    assert len(img_bytes) < API_SIZE_LIMIT, (
        f"Image {len(img_bytes)/1024:.0f} KB exceeds {API_SIZE_LIMIT/1024:.0f} KB"
    )


def test_capture_dimensions_positive():
    _, w, h = screen.capture()
    assert w > 0 and h > 0


def test_capture_long_edge_within_limit():
    img_bytes, _, _ = screen.capture()
    img = Image.open(io.BytesIO(img_bytes))
    assert max(img.size) <= MAX_LONG_EDGE, (
        f"Long edge {max(img.size)}px exceeds {MAX_LONG_EDGE}px"
    )


def test_media_type_is_jpeg():
    img_bytes, _, _ = screen.capture()
    assert img_bytes[:2] == b'\xff\xd8', "Must be JPEG"
