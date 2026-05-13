"""
Ticket #2: Physics rule W1 not wired — pump→pressure transient detection missing.
W1 fires when a pump-downstream junction shows a pressure swing > threshold
over the last PUMP_PRESSURE_CHECK_WINDOW ticks, indicating a pump-induced transient.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.layer3_twin import DigitalTwin
from models.state_vector import NodeReading


def _reading(node_id: str, value: float, subsystem: str = "water") -> NodeReading:
    return NodeReading(
        node_id=node_id,
        subsystem=subsystem,
        metric="pressure" if subsystem == "water" else "vm_pu",
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


def _feed_ticks(twin: DigitalTwin, node_id: str, values: list, subsystem: str = "water"):
    """Feed a sequence of values for one node across consecutive ticks."""
    for i, v in enumerate(values):
        twin.update([_reading(node_id, v, subsystem)], tick=i)


def _w1_violations(twin: DigitalTwin) -> list:
    return [v for v in twin.active_violations if v.rule_id == "W1"]


class TestW1PumpPressureTransient(unittest.TestCase):

    def test_w1_fires_on_rapid_pressure_drop_at_pump_downstream_node(self):
        """W1 must fire when pump-downstream node '10' drops >10m in 3 ticks."""
        twin = DigitalTwin()
        # Stable warmup, then sharp drop: 35 → 35 → 35 → 20 → 14
        _feed_ticks(twin, "10", [35.0, 35.0, 35.0, 20.0, 14.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations, "W1 did not fire on rapid pressure drop at node '10'")

    def test_w1_fires_on_rapid_pressure_rise_at_pump_downstream_node(self):
        """W1 must fire on rapid pressure rise as well (pump start transient)."""
        twin = DigitalTwin()
        _feed_ticks(twin, "10", [14.0, 14.0, 14.0, 28.0, 35.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations, "W1 did not fire on rapid pressure rise at node '10'")

    def test_w1_fires_for_pump_335_downstream_node(self):
        """W1 must also apply to pump_335 downstream nodes ('35', '40', '50')."""
        twin = DigitalTwin()
        _feed_ticks(twin, "35", [40.0, 40.0, 40.0, 25.0, 18.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations, "W1 did not fire for pump_335 downstream node '35'")

    def test_w1_not_fired_on_stable_pressure(self):
        """W1 must NOT fire when pressure is stable (normal operation)."""
        twin = DigitalTwin()
        _feed_ticks(twin, "10", [35.0, 35.1, 34.9, 35.0, 35.2, 34.8, 35.0])
        violations = _w1_violations(twin)
        self.assertFalse(violations, "W1 spuriously fired on stable pressure")

    def test_w1_not_fired_on_gradual_drift_below_threshold(self):
        """W1 must NOT fire for slow pressure drift staying under the 3-tick threshold."""
        twin = DigitalTwin()
        # 1m drop per tick — over 3 ticks that's 3m, well below 10m threshold
        _feed_ticks(twin, "10", [35.0, 34.0, 33.0, 32.0, 31.0, 30.0, 29.0])
        violations = _w1_violations(twin)
        self.assertFalse(violations, "W1 fired on gradual drift that shouldn't trigger")

    def test_w1_does_not_fire_for_non_pump_adjacent_node(self):
        """W1 must NOT fire for node '117', which is not downstream of any pump."""
        twin = DigitalTwin()
        # Large swing on a non-pump node should not trigger W1
        _feed_ticks(twin, "117", [50.0, 50.0, 50.0, 20.0, 5.0])
        violations = _w1_violations(twin)
        self.assertFalse(violations, "W1 fired for non-pump-adjacent node '117'")

    def test_w1_lists_affected_downstream_node(self):
        """W1 violation must list the transient-affected node in affected_nodes."""
        twin = DigitalTwin()
        _feed_ticks(twin, "10", [35.0, 35.0, 35.0, 20.0, 14.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations)
        self.assertIn("10", violations[-1].affected_nodes)

    def test_w1_not_fired_with_single_reading(self):
        """W1 needs at least 2 readings in the window — single reading must be silent."""
        twin = DigitalTwin()
        twin.update([_reading("10", 35.0)], tick=0)
        violations = _w1_violations(twin)
        self.assertFalse(violations, "W1 fired with only one reading (no delta possible)")

    def test_w1_severity_is_high(self):
        """W1 violations must carry HIGH severity (pump transients are significant)."""
        twin = DigitalTwin()
        _feed_ticks(twin, "10", [35.0, 35.0, 35.0, 20.0, 14.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations)
        self.assertEqual(violations[-1].severity, "HIGH")

    def test_w1_subsystem_is_water(self):
        """W1 violation must be tagged subsystem='water'."""
        twin = DigitalTwin()
        _feed_ticks(twin, "10", [35.0, 35.0, 35.0, 20.0, 14.0])
        violations = _w1_violations(twin)
        self.assertTrue(violations)
        self.assertEqual(violations[-1].subsystem, "water")


if __name__ == "__main__":
    unittest.main()
