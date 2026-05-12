"""
Ticket #5: Dashboard row-3 (and row-1) grid overflows at < 1400px.
Fix: add @media (max-width: 1399px) block that collapses both grids to 1fr.
Tests parse dashboard.css to verify the breakpoint and column rules exist.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_CSS_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "css", "dashboard.css")


def _load_css() -> str:
    with open(_CSS_PATH, encoding="utf-8") as f:
        return f.read()


def _extract_media_block(css: str, max_width_px: int) -> str:
    """Return the body of the first @media block whose max-width is <= max_width_px."""
    pattern = r'@media\s*\([^)]*max-width\s*:\s*(\d+)px[^)]*\)\s*\{((?:[^{}]|\{[^{}]*\})*)\}'
    for m in re.finditer(pattern, css, re.DOTALL):
        width = int(m.group(1))
        if width <= max_width_px:
            return m.group(2)
    return ""


def _selector_property(css_block: str, selector: str, prop: str) -> str:
    """Find the value of `prop` inside `selector { ... }` within css_block."""
    sel_pattern = re.escape(selector) + r'\s*\{([^}]*)\}'
    m = re.search(sel_pattern, css_block, re.DOTALL)
    if not m:
        return ""
    rules = m.group(1)
    prop_m = re.search(re.escape(prop) + r'\s*:\s*([^;]+)', rules)
    return prop_m.group(1).strip() if prop_m else ""


class TestDashboardResponsiveBreakpoint(unittest.TestCase):

    def setUp(self):
        self.css = _load_css()

    # --- breakpoint presence ---

    def test_media_query_exists_at_or_below_1400px(self):
        """A @media max-width breakpoint at ≤ 1400px must exist in dashboard.css."""
        block = _extract_media_block(self.css, 1400)
        self.assertTrue(block,
            "@media (max-width: 1399px) or similar not found — no responsive breakpoint")

    def test_media_query_targets_narrow_screens_not_mobile_only(self):
        """Breakpoint must be in the 1200–1400px range (laptop-screen fix, not just mobile)."""
        pattern = r'@media\s*\([^)]*max-width\s*:\s*(\d+)px[^)]*\)'
        widths = [int(m.group(1)) for m in re.finditer(pattern, self.css)]
        in_range = [w for w in widths if 1200 <= w <= 1400]
        self.assertTrue(in_range,
            f"No breakpoint in 1200–1400px range found; breakpoints present: {widths}")

    # --- row-3 responsive rules ---

    def test_row3_grid_overridden_in_narrow_media_query(self):
        """Inside the ≤1400px breakpoint, .row-3 must override grid-template-columns."""
        block = _extract_media_block(self.css, 1400)
        self.assertIn(".row-3", block,
            ".row-3 not targeted inside the narrow-screen media query")

    def test_row3_collapses_to_single_column_below_breakpoint(self):
        """Inside the breakpoint, .row-3 must use a single-column layout (1fr)."""
        block = _extract_media_block(self.css, 1400)
        cols = _selector_property(block, ".row-3", "grid-template-columns")
        self.assertEqual(cols, "1fr",
            f".row-3 grid-template-columns inside breakpoint is '{cols}', expected '1fr'")

    # --- row-1 responsive rules ---

    def test_row1_grid_overridden_in_narrow_media_query(self):
        """Inside the ≤1400px breakpoint, .row-1 must also override grid-template-columns."""
        block = _extract_media_block(self.css, 1400)
        self.assertIn(".row-1", block,
            ".row-1 not targeted inside the narrow-screen media query")

    def test_row1_collapses_to_single_column_below_breakpoint(self):
        """Inside the breakpoint, .row-1 must use a single-column layout (1fr)."""
        block = _extract_media_block(self.css, 1400)
        cols = _selector_property(block, ".row-1", "grid-template-columns")
        self.assertEqual(cols, "1fr",
            f".row-1 grid-template-columns inside breakpoint is '{cols}', expected '1fr'")

    # --- normal (wide) layout unchanged ---

    def test_row3_three_column_layout_preserved_at_full_width(self):
        """Outside any media query, .row-3 must still have its 3-column layout."""
        # Strip all @media blocks, then check .row-3 still has 25%/35%/40% columns
        stripped = re.sub(r'@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}', '', self.css, flags=re.DOTALL)
        cols = _selector_property(stripped, ".row-3", "grid-template-columns")
        self.assertTrue(cols and "%" in cols,
            f"Base .row-3 layout changed; got '{cols}' — preserve the 3-column desktop grid")

    def test_row1_three_column_layout_preserved_at_full_width(self):
        """Outside any media query, .row-1 must still have its 3-column layout."""
        stripped = re.sub(r'@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}', '', self.css, flags=re.DOTALL)
        cols = _selector_property(stripped, ".row-1", "grid-template-columns")
        self.assertTrue(cols and "%" in cols,
            f"Base .row-1 layout changed; got '{cols}' — preserve the 3-column desktop grid")


if __name__ == "__main__":
    unittest.main()
