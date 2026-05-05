"""
Code-review fixes for W2:
  HIGH-1: current reading must be excluded from baseline window — the detector
          needs WARMUP_TICKS+1 history entries so the baseline is purely pre-event.
  HIGH-2: low-and-slow 0.1 m/tick ramp that evades sigma detection must still
          fire W2 via a secondary oldest-vs-current absolute-drop check.
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


def _w2_fired(twin: DigitalTwin) -> bool:
    return any(v.rule_id == "W2" for v in twin.active_violations)


class TestW2BaselineExclusion(unittest.TestCase):
    """HIGH-1: current reading must not be included in its own baseline window.

    With the old code the boundary is WARMUP_TICKS: at exactly WARMUP_TICKS
    entries (including the current attack reading) the rule evaluates and fires.
    The fix raises the boundary to WARMUP_TICKS+1 and slices baseline as
    hist[-(W2_BASELINE_WINDOW+1):-1] so the attack reading is never part of the
    reference distribution used to detect it.
    """

    def setUp(self):
        self.twin = DigitalTwin()

    def test_attack_at_warmup_ticks_boundary_does_not_fire(self):
        """29 stable readings + 1 attack = exactly W2_WARMUP_TICKS entries.

        OLD code: len=30 >= W2_WARMUP_TICKS(30) → evaluates → fires (false positive
        because baseline is only 29 readings, insufficient reference).
        NEW code: len=30 < W2_WARMUP_TICKS+1(31) → skips → no fire.
        """
        for t in range(config.W2_WARMUP_TICKS - 1):      # 29 stable readings
            self.twin.update([_reading("node_bnd", 35.0)], tick=t)
        self.twin.update([_reading("node_bnd", 0.0)],      # attack on 30th tick
                         tick=config.W2_WARMUP_TICKS - 1)
        self.assertFalse(_w2_fired(self.twin),
            "W2 fired with only W2_WARMUP_TICKS total entries — "
            "needs WARMUP_TICKS+1 so baseline excludes the current reading")

    def test_attack_at_warmup_plus_one_fires(self):
        """30 stable + 1 attack = WARMUP_TICKS+1 entries — detector must fire."""
        for t in range(config.W2_WARMUP_TICKS):           # 30 stable readings
            self.twin.update([_reading("node_bnd2", 35.0)], tick=t)
        self.twin.update([_reading("node_bnd2", 0.0)],     # attack on 31st tick
                         tick=config.W2_WARMUP_TICKS)
        self.assertTrue(_w2_fired(self.twin),
            "W2 did not fire with WARMUP_TICKS+1 entries and a 35→0 m drop")

    def test_stable_node_at_boundary_does_not_false_positive(self):
        """29 stable + 1 stable (same value) must not fire regardless of boundary."""
        for t in range(config.W2_WARMUP_TICKS - 1):
            self.twin.update([_reading("node_stbl", 10.0)], tick=t)
        self.twin.update([_reading("node_stbl", 10.0)], tick=config.W2_WARMUP_TICKS - 1)
        self.assertFalse(_w2_fired(self.twin),
            "W2 fired for a stable node at exactly the warmup boundary")


class TestW2RampDetection(unittest.TestCase):
    """HIGH-2: a 0.1 m/tick gradual ramp that evades the sigma check must still
    trigger W2 via an absolute oldest-vs-current drop comparison.

    Verification: with ONLY the sigma path, 0.1 m/tick never fires because the
    rolling window absorbs the ramp into its mean.  The secondary check fires when
    current < oldest_in_baseline_window - W2_MIN_DROP_M.
    """

    def setUp(self):
        self.twin = DigitalTwin()

    def _warm_up(self, node_id: str, value: float):
        for t in range(config.W2_WARMUP_TICKS):
            self.twin.update([_reading(node_id, value)], tick=t)

    def test_slow_0_1m_ramp_triggers_w2(self):
        """0.1 m/tick drop — sigma path cannot catch this; ramp check must fire."""
        self._warm_up("node_slow", 35.0)
        current = 35.0
        fired = False
        # Run for BASELINE_WINDOW+5 ticks — ramp check fires when drop >= W2_MIN_DROP_M
        for i in range(config.W2_BASELINE_WINDOW + 5):
            current -= 0.1
            self.twin.update([_reading("node_slow", current)],
                             tick=config.W2_WARMUP_TICKS + i + 1)
            if _w2_fired(self.twin):
                fired = True
                break
        self.assertTrue(fired,
            "W2 never fired for 0.1 m/tick ramp — secondary ramp check missing "
            "(sigma path alone cannot catch low-and-slow attacks)")

    def test_slow_ramp_fires_within_baseline_window_ticks(self):
        """Ramp detection must trigger within W2_BASELINE_WINDOW ticks of attack start."""
        self._warm_up("node_slow2", 30.0)
        current = 30.0
        fire_tick = None
        for i in range(config.W2_BASELINE_WINDOW):
            current -= 0.1
            tick = config.W2_WARMUP_TICKS + i + 1
            self.twin.update([_reading("node_slow2", current)], tick=tick)
            if _w2_fired(self.twin) and fire_tick is None:
                fire_tick = tick
        self.assertIsNotNone(fire_tick,
            "Ramp detection did not fire within W2_BASELINE_WINDOW ticks — "
            "check fires too late or not at all")

    def test_tiny_drift_below_min_drop_never_triggers(self):
        """0.05 m/tick over 30 ticks = 1.5 m total (< W2_MIN_DROP_M) must NOT fire."""
        self._warm_up("node_drift", 25.0)
        current = 25.0
        for i in range(config.W2_BASELINE_WINDOW):
            current -= 0.05    # total drop = 1.5 m < W2_MIN_DROP_M (3.0)
            self.twin.update([_reading("node_drift", current)],
                             tick=config.W2_WARMUP_TICKS + i + 1)
        self.assertFalse(_w2_fired(self.twin),
            "W2 fired for 1.5 m total drift — ramp threshold is too sensitive")

    def test_ramp_on_low_baseline_node_fires_when_drop_exceeds_threshold(self):
        """A node at 4 m baseline (like Net3 node 40) that ramps down to 1 m must fire."""
        self._warm_up("node_low", 4.0)
        current = 4.0
        fired = False
        for i in range(config.W2_BASELINE_WINDOW + 5):
            current -= 0.1
            if current < 0:
                current = 0.0
            self.twin.update([_reading("node_low", current)],
                             tick=config.W2_WARMUP_TICKS + i + 1)
            if _w2_fired(self.twin):
                fired = True
                break
        self.assertTrue(fired,
            "W2 did not fire when a low-baseline (4 m) node dropped below 1 m")

    def test_ramp_does_not_cause_false_positive_on_stable_nearby_node(self):
        """A ramp on node A must not bleed into W2 violations for an unrelated stable node B."""
        self._warm_up("node_A", 35.0)
        self._warm_up("node_B", 20.0)

        current_a = 35.0
        for i in range(config.W2_BASELINE_WINDOW + 5):
            current_a -= 0.1
            tick = config.W2_WARMUP_TICKS + i + 1
            self.twin.update([
                _reading("node_A", current_a),
                _reading("node_B", 20.0),   # stable — must never appear in W2
            ], tick=tick)

        w2_affected = []
        for v in self.twin.active_violations:
            if v.rule_id == "W2":
                w2_affected.extend(v.affected_nodes)

        self.assertNotIn("node_B", w2_affected,
            "Stable node_B appeared in W2 affected_nodes — ramp detection leaked across nodes")


if __name__ == "__main__":
    unittest.main()
