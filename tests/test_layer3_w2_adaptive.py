"""
W2 adaptive baseline: pressure-underflow detection should use a per-node
rolling baseline (mean ± k·sigma) rather than a fixed 5 m threshold.

Goals:
  - Nodes that are naturally low-pressure at baseline must NOT trigger W2.
  - A sudden drop well below a node's established baseline MUST trigger W2.
  - W2 must not fire during the warm-up period (< W2_WARMUP_TICKS history).
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from layers.layer3_twin import DigitalTwin
from models.state_vector import NodeReading


def _reading(node_id: str, value: float) -> NodeReading:
    return NodeReading(
        node_id=node_id,
        subsystem="water",
        metric="pressure",
        value=value,
        unit="m",
        protocol="Modbus/TCP",
        timestamp_iso="2026-01-01T00:00:00+00:00",
        timestamp_ms=0,
        confidence=1.0,
        source="SIMULATED",
        integrity_hash="",
        status="NORMAL",
    )


def _w2_violations(twin: DigitalTwin) -> list:
    return [v for v in twin.active_violations if v.rule_id == "W2"]


def _warm_up(twin: DigitalTwin, node_id: str, value: float, n_ticks: int = None):
    """Feed a stable value for n_ticks to build the rolling baseline."""
    n = n_ticks if n_ticks is not None else config.W2_WARMUP_TICKS
    for t in range(n):
        twin.update([_reading(node_id, value)], tick=t)


class TestW2AdaptiveBaseline(unittest.TestCase):

    def setUp(self):
        self.twin = DigitalTwin()

    # ------------------------------------------------------------------
    # Warm-up guard
    # ------------------------------------------------------------------

    def test_w2_does_not_fire_during_warmup(self):
        """W2 must not fire before W2_WARMUP_TICKS ticks of history are collected."""
        n = config.W2_WARMUP_TICKS - 1
        for t in range(n):
            self.twin.update([_reading("node_A", 0.0)], tick=t)
        self.assertEqual(_w2_violations(self.twin), [],
            "W2 fired before warm-up period completed")

    # ------------------------------------------------------------------
    # Baseline nodes that are naturally low — must NOT trigger
    # ------------------------------------------------------------------

    def test_stable_low_pressure_node_does_not_trigger_w2(self):
        """A node at 0 m baseline must not trigger W2 when it stays at 0 m."""
        _warm_up(self.twin, "node_low", 0.0)
        # one more tick at same value
        self.twin.update([_reading("node_low", 0.0)], tick=config.W2_WARMUP_TICKS)
        self.assertEqual(_w2_violations(self.twin), [],
            "W2 incorrectly fired for a stable low-pressure baseline node")

    def test_node_40_equivalent_does_not_trigger_w2(self):
        """A node stabilised at ~4 m (like Net3 node 40) must not trigger W2."""
        _warm_up(self.twin, "node_40eq", 4.0)
        self.twin.update([_reading("node_40eq", 4.0)], tick=config.W2_WARMUP_TICKS)
        self.assertEqual(_w2_violations(self.twin), [],
            "W2 fired for node with 4 m baseline — this is a false positive")

    # ------------------------------------------------------------------
    # Real attack drops — MUST trigger
    # ------------------------------------------------------------------

    def test_sudden_large_drop_triggers_w2(self):
        """A node at 35 m baseline that suddenly drops to 5 m must trigger W2."""
        _warm_up(self.twin, "node_B", 35.0)
        self.twin.update([_reading("node_B", 5.0)], tick=config.W2_WARMUP_TICKS)
        self.assertNotEqual(_w2_violations(self.twin), [],
            "W2 did not fire for a large sudden pressure drop (35 → 5 m)")

    def test_w2_includes_affected_node_id(self):
        """When W2 fires, the affected node must appear in affected_nodes."""
        _warm_up(self.twin, "node_C", 30.0)
        self.twin.update([_reading("node_C", 0.0)], tick=config.W2_WARMUP_TICKS)
        violations = _w2_violations(self.twin)
        self.assertTrue(any("node_C" in v.affected_nodes for v in violations),
            "Affected node ID missing from W2 violation")

    def test_moderate_drop_below_sigma_threshold_triggers_w2(self):
        """A drop of > W2_SIGMA_THRESHOLD * std below mean must trigger W2."""
        baseline = 20.0
        # inject slight noise to build a real std
        import math
        noisy = [baseline + math.sin(t) * 0.2 for t in range(config.W2_WARMUP_TICKS)]
        for t, v in enumerate(noisy):
            self.twin.update([_reading("node_D", v)], tick=t)
        # now drop far below (baseline - 15m, way beyond any sigma)
        self.twin.update([_reading("node_D", baseline - 15.0)], tick=config.W2_WARMUP_TICKS)
        self.assertNotEqual(_w2_violations(self.twin), [],
            "W2 did not fire for a drop well below sigma threshold")

    # ------------------------------------------------------------------
    # Small fluctuations — must NOT trigger
    # ------------------------------------------------------------------

    def test_small_noise_does_not_trigger_w2(self):
        """Normal sensor noise (+/- 0.5 m around baseline) must not trigger W2."""
        _warm_up(self.twin, "node_E", 25.0)
        # Small perturbation — within noise range
        self.twin.update([_reading("node_E", 24.6)], tick=config.W2_WARMUP_TICKS)
        self.assertEqual(_w2_violations(self.twin), [],
            "W2 fired for a minor fluctuation — threshold is too sensitive")

    # ------------------------------------------------------------------
    # Pump nodes excluded
    # ------------------------------------------------------------------

    def test_pump_nodes_excluded_from_w2(self):
        """pump_* nodes must never appear in W2 affected_nodes."""
        _warm_up(self.twin, "pump_10", 0.0)
        self.twin.update([_reading("pump_10", 0.0)], tick=config.W2_WARMUP_TICKS)
        for v in _w2_violations(self.twin):
            self.assertNotIn("pump_10", v.affected_nodes,
                "pump node incorrectly included in W2 violation")


if __name__ == "__main__":
    unittest.main()
