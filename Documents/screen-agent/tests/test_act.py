"""
TDD — RED: coordinate calibration tests for click_at in act.py.

Bugs under test:
  1. int() truncates instead of round() — produces systematic ≤0.5px errors
  2. No clamping — x_pct ≥ 1.0 gives out-of-bounds px; negative pcts are negative px

Isolation note:
  test_abort.py and test_agent_dispatch.py inject stubs via
  sys.modules['act'] = <stub> (direct assign).  We pop 'act' and reimport the
  real module so our tests run against the live code, not a MagicMock.
  We then grab whichever pyautogui object act.py bound at import time so
  moveTo assertions target the right mock.
"""

import sys
import os
import types
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Stubs (setdefault — don't evict stubs another file already installed) ─────

def _ensure_stub(name: str, **attrs) -> types.ModuleType:
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
    return sys.modules[name]


_ensure_stub('gi',                  require_version=mock.MagicMock())
_ensure_stub('gi.repository')
_ensure_stub('gi.repository.Gtk')
_ensure_stub('gi.repository.Gdk')
_ensure_stub('pyautogui',
             PAUSE=0, FAILSAFE=True,
             moveTo=mock.MagicMock(), click=mock.MagicMock(),
             easeInOutQuad=lambda t: t)

# Patch gi.repository attributes so act.py's `from gi.repository import Gtk, Gdk` works
_repo = sys.modules['gi.repository']
if not hasattr(_repo, 'Gtk'):
    _repo.Gtk = sys.modules['gi.repository.Gtk']
if not hasattr(_repo, 'Gdk'):
    _repo.Gdk = sys.modules['gi.repository.Gdk']

# Force-reload the real act.py (other test files assign a stub directly into
# sys.modules['act'], which would make our tests hit MagicMock, not click_at).
sys.modules.pop('act', None)
import act  # noqa: E402

# Bind to whichever pyautogui act.py actually imported — this is the object
# whose .moveTo we need to inspect.
import pyautogui as _pag  # noqa: E402

# Guarantee moveTo / click are MagicMocks (in case a real pyautogui slipped in).
if not isinstance(getattr(_pag, 'moveTo', None), mock.MagicMock):
    _pag.moveTo = mock.MagicMock()
if not isinstance(getattr(_pag, 'click', None), mock.MagicMock):
    _pag.click = mock.MagicMock()


# ── Helper ────────────────────────────────────────────────────────────────────

def _moved_to() -> tuple[int, int]:
    """Return (px, py) that click_at passed to pyautogui.moveTo."""
    args, _ = _pag.moveTo.call_args
    return args[0], args[1]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestClickAtCoordinateMapping:
    def setup_method(self):
        _pag.moveTo.reset_mock()
        _pag.click.reset_mock()

    # ── happy-path sanity ──────────────────────────────────────────────────

    def test_center_fraction_maps_to_screen_center(self):
        act.click_at(0.5, 0.5, 1920, 1080)
        px, py = _moved_to()
        assert px == 960, f"expected 960, got {px}"
        assert py == 540, f"expected 540, got {py}"

    def test_top_left_fraction_maps_to_origin(self):
        act.click_at(0.0, 0.0, 1920, 1080)
        px, py = _moved_to()
        assert px == 0 and py == 0

    def test_non_standard_resolution_maps_correctly(self):
        act.click_at(0.5, 0.5, 2560, 1440)
        px, py = _moved_to()
        assert px == round(0.5 * 2560)
        assert py == round(0.5 * 1440)

    # ── rounding (bug 1) ──────────────────────────────────────────────────

    def test_rounding_not_truncation_x(self):
        # 0.3336 * 1920 = 640.512  →  int() = 640 (wrong), round() = 641 (correct)
        act.click_at(0.3336, 0.5, 1920, 1080)
        px, _ = _moved_to()
        expected = round(0.3336 * 1920)
        assert px == expected, (
            f"expected round()={expected}, got {px} "
            "(likely int() truncation — use round() instead)"
        )

    def test_rounding_not_truncation_y(self):
        # 0.4996 * 1080 = 539.568  →  int() = 539, round() = 540
        act.click_at(0.5, 0.4996, 1920, 1080)
        _, py = _moved_to()
        expected = round(0.4996 * 1080)
        assert py == expected, (
            f"expected round()={expected}, got {py} (int() truncation bug)"
        )

    # ── coordinate clamping (bug 2) ────────────────────────────────────────

    def test_pct_exactly_1_0_stays_within_screen(self):
        # int(1.0 * 1920) = 1920 — OUT OF BOUNDS (max valid = 1919)
        act.click_at(1.0, 1.0, 1920, 1080)
        px, py = _moved_to()
        assert px <= 1919, f"px={px} exceeds max valid x 1919"
        assert py <= 1079, f"py={py} exceeds max valid y 1079"

    def test_pct_greater_than_1_is_clamped(self):
        act.click_at(1.05, 0.5, 1920, 1080)
        px, _ = _moved_to()
        assert px <= 1919, f"unclamped px={px} exceeds screen width"

    def test_negative_pct_is_clamped_to_zero(self):
        act.click_at(-0.1, -0.2, 1920, 1080)
        px, py = _moved_to()
        assert px >= 0, f"negative px={px}"
        assert py >= 0, f"negative py={py}"

    def test_clamping_preserves_valid_coordinates(self):
        # A valid in-range fraction must not be affected by clamping logic
        act.click_at(0.75, 0.25, 1920, 1080)
        px, py = _moved_to()
        assert px == round(0.75 * 1920)
        assert py == round(0.25 * 1080)
