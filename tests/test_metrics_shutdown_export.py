"""
Ticket #6: Metrics TTD table only exports on manual GET /api/report.
Fix: extract _on_shutdown(tick) called in main() try/finally, so reports
are written automatically whenever the server process stops.
"""
import os
import sys
import unittest
from unittest.mock import patch, call, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _on_shutdown


class TestShutdownExport(unittest.TestCase):

    def test_on_shutdown_calls_export_report(self):
        """_on_shutdown must call metrics.export_report exactly once."""
        with patch("main.metrics.export_report") as mock_export:
            _on_shutdown(tick=5)
        mock_export.assert_called_once()

    def test_on_shutdown_passes_tick_to_export_report(self):
        """_on_shutdown must forward the tick argument to export_report."""
        with patch("main.metrics.export_report") as mock_export:
            _on_shutdown(tick=42)
        mock_export.assert_called_once_with(42)

    def test_on_shutdown_at_tick_zero(self):
        """_on_shutdown must export even at tick 0 (immediate stop after start)."""
        with patch("main.metrics.export_report") as mock_export:
            _on_shutdown(tick=0)
        mock_export.assert_called_once_with(0)

    def test_on_shutdown_at_large_tick(self):
        """_on_shutdown must handle large tick values (long-running demos)."""
        with patch("main.metrics.export_report") as mock_export:
            _on_shutdown(tick=9999)
        mock_export.assert_called_once_with(9999)

    def test_on_shutdown_does_not_suppress_export_errors(self):
        """If export_report raises, _on_shutdown must not silently swallow it."""
        with patch("main.metrics.export_report", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                _on_shutdown(tick=10)

    def test_on_shutdown_returns_export_result(self):
        """_on_shutdown should return whatever export_report returns (the summary dict)."""
        fake_summary = {"comparison_table": [], "me_dt": {}}
        with patch("main.metrics.export_report", return_value=fake_summary) as mock_export:
            result = _on_shutdown(tick=7)
        self.assertEqual(result, fake_summary)

    def test_on_shutdown_not_called_twice_for_single_shutdown(self):
        """Calling _on_shutdown once must trigger exactly one export, not more."""
        with patch("main.metrics.export_report") as mock_export:
            _on_shutdown(tick=3)
        self.assertEqual(mock_export.call_count, 1)


class TestMainFinallyHook(unittest.TestCase):
    """Verify that main.py wires _on_shutdown into the server teardown path."""

    def test_main_source_contains_try_finally_with_on_shutdown(self):
        """main() must have a try/finally that calls _on_shutdown — parse source as guard."""
        import inspect
        import main as main_module
        src = inspect.getsource(main_module.main)
        self.assertIn("finally", src,
            "main() has no finally block — _on_shutdown will not run on Ctrl+C")
        self.assertIn("_on_shutdown", src,
            "main() finally block does not call _on_shutdown")


if __name__ == "__main__":
    unittest.main()
