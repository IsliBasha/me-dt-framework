"""
Ticket #7: IsolationForest excludes synthetic traffic from its feature vector
but this is never shown in the UI baseline table.
Fix: add a traffic-exclusion note to the IsoForest algorithm cell in index.html.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")


def _load_html() -> str:
    with open(_HTML_PATH, encoding="utf-8") as f:
        return f.read()


def _isoforest_row(html: str) -> str:
    """Extract the full <tr> block that contains the IsoForest detector row."""
    m = re.search(r'(<tr>(?:[^<]|<(?!tr>))*?IsoForest.*?</tr>)', html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ""


class TestIsoForestTrafficNote(unittest.TestCase):

    def setUp(self):
        self.html = _load_html()
        self.isoforest_row = _isoforest_row(self.html)

    def test_isoforest_row_exists(self):
        """Sanity: IsoForest row must be present in the table."""
        self.assertTrue(self.isoforest_row,
            "Could not find IsoForest row in index.html baseline table")

    def test_isoforest_algorithm_cell_mentions_traffic_exclusion(self):
        """IsoForest algorithm cell must contain a traffic-exclusion note."""
        row_lower = self.isoforest_row.lower()
        has_note = "traffic" in row_lower and (
            "excl" in row_lower or "exclud" in row_lower or "no traffic" in row_lower
        )
        self.assertTrue(has_note,
            "IsoForest row has no traffic-exclusion note — examiner cannot see this design choice")

    def test_isoforest_still_shows_liu_citation(self):
        """IsoForest row must still show the Liu et al. citation after the note is added."""
        self.assertIn("Liu", self.isoforest_row,
            "Liu et al. citation was removed from IsoForest row")

    def test_cusum_row_does_not_have_spurious_traffic_exclusion_note(self):
        """CUSUM row must NOT mention traffic exclusion (it's not relevant there)."""
        cusum_m = re.search(r'<tr>(?:[^<]|<(?!tr>))*?CUSUM.*?</tr>', self.html, re.DOTALL | re.IGNORECASE)
        if cusum_m:
            cusum_row = cusum_m.group(0).lower()
            self.assertNotIn("excl", cusum_row,
                "CUSUM row unexpectedly contains an exclusion note")

    def test_note_is_in_algorithm_column_not_detector_name(self):
        """The traffic note must appear in the last <td> (algorithm), not in the detector name cell."""
        tds = re.findall(r'<td[^>]*>(.*?)</td>', self.isoforest_row, re.DOTALL | re.IGNORECASE)
        self.assertGreater(len(tds), 0, "No <td> cells found in IsoForest row")
        # The first cell is the detector name — it should not contain the note
        first_td = tds[0].lower()
        self.assertNotIn("excl", first_td,
            "Traffic exclusion note incorrectly placed in detector-name cell")
        # The last cell (algorithm) should contain the note
        last_td = tds[-1].lower()
        self.assertIn("traffic", last_td,
            "Traffic exclusion note not found in algorithm (last) cell")


if __name__ == "__main__":
    unittest.main()
