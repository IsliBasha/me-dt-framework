"""
Ticket #1: Water node "10" shows negative pressure at tick 0.
Root cause: WNTR hydraulic artifact before steady-state convergence.
Fix: clamp p_val = max(0.0, p_val) in run_water_tick before emitting telemetry.
"""
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def _make_pressure_results(pressure_map: dict) -> MagicMock:
    df = pd.DataFrame({nid: [v] for nid, v in pressure_map.items()})
    results = MagicMock()
    results.node = {
        "pressure": df,
        "head":     df,
        "demand":   df,
    }
    results.link = {
        "flowrate": MagicMock(),
        "velocity": MagicMock(),
    }
    return results


def _make_wn_mock(node_ids: list) -> MagicMock:
    wn = MagicMock()
    wn.junction_name_list = node_ids
    wn.pump_name_list = []
    wn.get_node.side_effect = lambda nid: MagicMock() if nid in node_ids else None
    return wn


def _run(pressure_map: dict) -> dict:
    """Run run_water_tick with WNTR returning the given pressure_map."""
    import layers.layer1_physical as l1
    wn = _make_wn_mock(list(pressure_map.keys()))
    results = _make_pressure_results(pressure_map)
    with patch.object(l1, "_WNTR_OK", True), \
         patch("layers.layer1_physical.wntr") as mock_wntr:
        mock_wntr.sim.WNTRSimulator.return_value.run_sim.return_value = results
        return l1.run_water_tick(wn, {})


class TestWaterPressureClamping(unittest.TestCase):

    def test_node_10_first_tick_negative_artifact_clamped_to_zero(self):
        """Regression: tick-0 artifact of -0.45 m on node '10' must become 0.0."""
        telemetry = _run({"10": -0.45})
        self.assertEqual(telemetry["10"]["pressure"], 0.0,
                         "node '10' returned negative pressure — WNTR artifact not clamped")

    def test_negative_pressure_always_clamped(self):
        """Any negative pressure value in WNTR output must be clamped to 0.0."""
        telemetry = _run({"10": -0.45, "15": -12.3, "20": -0.001})
        for nid in ("10", "15", "20"):
            self.assertGreaterEqual(telemetry[nid]["pressure"], 0.0,
                                    f"Node {nid} still has negative pressure")

    def test_positive_pressure_passes_through_unchanged(self):
        """Positive WNTR pressure values must not be altered."""
        telemetry = _run({"15": 32.1})
        self.assertAlmostEqual(telemetry["15"]["pressure"], 32.1, places=5)

    def test_zero_pressure_unchanged(self):
        """Zero is a valid (if unusual) pressure and must not be modified."""
        telemetry = _run({"20": 0.0})
        self.assertEqual(telemetry["20"]["pressure"], 0.0)

    def test_all_display_nodes_non_negative_when_wntr_returns_negatives(self):
        """All WATER_DISPLAY_NODES must have pressure >= 0 even if WNTR is pathological."""
        pressure_map = {nid: -abs(hash(nid)) % 5 - 0.01 for nid in config.WATER_DISPLAY_NODES}
        telemetry = _run(pressure_map)
        for nid in config.WATER_DISPLAY_NODES:
            if nid in telemetry:
                self.assertGreaterEqual(
                    telemetry[nid]["pressure"], 0.0,
                    msg=f"WATER_DISPLAY_NODE '{nid}' returned negative pressure"
                )

    def test_high_pressure_node_correct_value(self):
        """Sanity: large valid pressures (e.g. 58.7 m) pass through exactly."""
        telemetry = _run({"117": 58.7})
        self.assertAlmostEqual(telemetry["117"]["pressure"], 58.7, places=5)

    def test_mixed_positive_and_negative_nodes(self):
        """Mixed batch: negative nodes clamped, positive nodes unchanged."""
        telemetry = _run({"10": -0.45, "15": 32.1, "20": -1.0, "35": 41.5})
        self.assertEqual(telemetry["10"]["pressure"], 0.0)
        self.assertAlmostEqual(telemetry["15"]["pressure"], 32.1, places=5)
        self.assertEqual(telemetry["20"]["pressure"], 0.0)
        self.assertAlmostEqual(telemetry["35"]["pressure"], 41.5, places=5)


if __name__ == "__main__":
    unittest.main()
