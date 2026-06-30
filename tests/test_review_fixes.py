"""
Regression tests for the 15 code-review findings filed against commit 830c3e6.
Each class maps to one finding and is RED before the corresponding fix.

Findings covered here: 1, 2, 3, 4, 5, 6, 8, 10, 11, 13
Findings intentionally skipped:
  7  -- quarantine_node wn/net wiring (requires FastAPI TestClient)
  9  -- pump reads wn vs wn_snap (requires deep WNTR control-rule setup)
  12 -- bare-except logging (observability fix, no boolean contract to assert)
  14 -- IsoForest zero-pad baseline (mitigated by fixing Finding 11)
  15 -- deepcopy performance (correctness-neutral; left as TODO comment)
"""
import sys
import os
import hashlib
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import wntr as _wntr
    _WNTR_OK = True
except ImportError:
    _WNTR_OK = False

from models.state_vector import NodeReading, AnomalyEvent
from layers.layer2_ingestion import process_batch
from layers.layer3_twin import DigitalTwin
from baselines import cusum_detector, isolation_forest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pump_raw(pump_id: str = "10", status_val: float = 1.0, corrupt_hash: bool = False) -> dict:
    ts_ms = 1_000
    good_hash = hashlib.sha256(f"pump_{pump_id}{status_val}{ts_ms}".encode()).hexdigest()[:16]
    return {
        "value":         status_val,
        "unit":          "",
        "status":        "LinkStatus.Open" if status_val else "LinkStatus.Closed",
        "subsystem":     "water",
        "pump":          True,
        "timestamp_ms":  ts_ms,
        "timestamp_iso": "2026-01-01T00:00:00+00:00",
        "integrity_hash": "deadbeefdeadbeef" if corrupt_hash else good_hash,
    }


def _pressure_raw(node_id: str = "10", pressure: float = 35.0) -> dict:
    ts_ms = 1_000
    h = hashlib.sha256(f"{node_id}{pressure}{ts_ms}".encode()).hexdigest()[:16]
    return {
        "pressure":      pressure,
        "unit":          "m",
        "status":        "NORMAL",
        "subsystem":     "water",
        "source":        "SIMULATED",
        "timestamp_ms":  ts_ms,
        "timestamp_iso": "2026-01-01T00:00:00+00:00",
        "integrity_hash": h,
    }


def _pump_reading(node_id: str = "pump_10", value: float = 1.0) -> NodeReading:
    return NodeReading(
        node_id=node_id,
        subsystem="water",
        metric="pump_status",
        value=value,
        unit="",
        protocol="Modbus/TCP",
        timestamp_iso="2026-01-01T00:00:00+00:00",
        timestamp_ms=1_000,
        confidence=1.0,
        source="SIMULATED",
        integrity_hash="",
        status="NORMAL",
    )


def _pressure_reading(node_id: str, value: float) -> NodeReading:
    return NodeReading(
        node_id=node_id,
        subsystem="water",
        metric="pressure",
        value=value,
        unit="m",
        protocol="Modbus/TCP",
        timestamp_iso="2026-01-01T00:00:00+00:00",
        timestamp_ms=1_000,
        confidence=1.0,
        source="SIMULATED",
        integrity_hash="",
        status="NORMAL",
    )


# ---------------------------------------------------------------------------
# Finding 1: CUSUM alert storm
# ---------------------------------------------------------------------------

class TestCUSUMExcludesPumpStatusNodes(unittest.TestCase):

    def setUp(self):
        cusum_detector.reset_all()

    def test_pump_status_nodes_produce_no_alerts(self):
        """After warmup with 1.0, a 0.0 pump-close must NOT fire a CUSUM alert."""
        for t in range(10):
            cusum_detector.process_tick([_pump_reading("pump_10", 1.0)], t)
        alerts = cusum_detector.process_tick([_pump_reading("pump_10", 0.0)], 10)
        self.assertEqual(alerts, [], "CUSUM must not alert on pump_status nodes")

    def test_pressure_nodes_still_generate_alerts(self):
        """Real pressure anomalies must still surface through CUSUM."""
        for t in range(10):
            cusum_detector.process_tick([_pressure_reading("n10", 35.0)], t)
        alerts = cusum_detector.process_tick([_pressure_reading("n10", 0.0)], 10)
        self.assertTrue(len(alerts) > 0, "CUSUM must still detect pressure drops")


# ---------------------------------------------------------------------------
# Finding 2: metric='pressure' for pump nodes
# ---------------------------------------------------------------------------

class TestPumpNodeMetric(unittest.TestCase):

    def test_pump_node_gets_pump_status_metric(self):
        batch = {"tick": 0, "water": {"pump_10": _pump_raw("10", 1.0)}, "power": {}, "traffic": {}}
        clean, _ = process_batch(batch, {})
        pump_reads = [r for r in clean if r.node_id == "pump_10"]
        self.assertTrue(pump_reads, "pump_10 must appear in clean stream")
        self.assertEqual(
            pump_reads[0].metric, "pump_status",
            f"Expected metric='pump_status', got '{pump_reads[0].metric}'"
        )

    def test_regular_water_node_still_gets_pressure_metric(self):
        batch = {"tick": 0, "water": {"10": _pressure_raw("10", 35.0)}, "power": {}, "traffic": {}}
        clean, _ = process_batch(batch, {})
        node_reads = [r for r in clean if r.node_id == "10"]
        self.assertTrue(node_reads)
        self.assertEqual(node_reads[0].metric, "pressure")


# ---------------------------------------------------------------------------
# Finding 3: Pump integrity hash bypass
# ---------------------------------------------------------------------------

class TestPumpIntegrityHash(unittest.TestCase):

    def test_wrong_hash_gives_zero_confidence(self):
        batch = {"tick": 0, "water": {"pump_10": _pump_raw("10", 1.0, corrupt_hash=True)}, "power": {}, "traffic": {}}
        clean, _ = process_batch(batch, {})
        pump_reads = [r for r in clean if r.node_id == "pump_10"]
        self.assertTrue(pump_reads)
        self.assertEqual(pump_reads[0].confidence, 0.0, "Pump with wrong hash must have confidence=0.0")

    def test_correct_hash_gives_full_confidence(self):
        batch = {"tick": 0, "water": {"pump_10": _pump_raw("10", 1.0, corrupt_hash=False)}, "power": {}, "traffic": {}}
        clean, _ = process_batch(batch, {})
        pump_reads = [r for r in clean if r.node_id == "pump_10"]
        self.assertTrue(pump_reads)
        self.assertEqual(pump_reads[0].confidence, 1.0)


# ---------------------------------------------------------------------------
# Finding 4: T2 never fires -- falsy-zero or-chain
# ---------------------------------------------------------------------------

class TestT2TrafficBlackout(unittest.TestCase):

    def _traffic_reading(self, node_id: str, flow: float) -> NodeReading:
        return NodeReading(
            node_id=node_id, subsystem="traffic", metric="vehicle_flow",
            value=flow, unit="veh/min", protocol="MQTT",
            timestamp_iso="2026-01-01T00:00:00+00:00", timestamp_ms=1_000,
            confidence=1.0, source="SYNTHETIC", integrity_hash="", status="NORMAL",
        )

    def test_t2_fires_with_three_zero_flow_nodes(self):
        twin = DigitalTwin()
        twin.update([
            self._traffic_reading("SYN-T01", 0.0),
            self._traffic_reading("SYN-T02", 0.0),
            self._traffic_reading("SYN-T03", 0.0),
            self._traffic_reading("SYN-T04", 50.0),
        ], tick=0)
        t2 = [v for v in twin.active_violations if v.rule_id == "T2"]
        self.assertTrue(t2, "T2 must fire when 3+ nodes have zero vehicle flow")

    def test_t2_silent_with_only_two_zero_flow_nodes(self):
        twin = DigitalTwin()
        twin.update([
            self._traffic_reading("SYN-T01", 0.0),
            self._traffic_reading("SYN-T02", 0.0),
            self._traffic_reading("SYN-T03", 50.0),
        ], tick=0)
        t2 = [v for v in twin.active_violations if v.rule_id == "T2"]
        self.assertFalse(t2, "T2 must not fire with only 2 zero-flow nodes")


# ---------------------------------------------------------------------------
# Finding 5: T1 never fires -- signal_phase stripped at Layer 2 boundary
# ---------------------------------------------------------------------------

class TestT1SignalAnomaly(unittest.TestCase):

    def _green_reading(self, node_id: str) -> NodeReading:
        return NodeReading(
            node_id=node_id, subsystem="traffic", metric="vehicle_flow",
            value=50.0, unit="veh/min", protocol="MQTT",
            timestamp_iso="2026-01-01T00:00:00+00:00", timestamp_ms=1_000,
            confidence=1.0, source="SYNTHETIC", integrity_hash="", status="NORMAL",
            signal_phase="GREEN",
        )

    def test_t1_fires_when_four_or_more_nodes_are_green(self):
        twin = DigitalTwin()
        twin.update([self._green_reading(f"SYN-T{i+1:02d}") for i in range(5)], tick=0)
        t1 = [v for v in twin.active_violations if v.rule_id == "T1"]
        self.assertTrue(t1, "T1 must fire when 4+ traffic nodes are GREEN")

    def test_t1_silent_with_fewer_than_four_green_nodes(self):
        twin = DigitalTwin()
        twin.update([self._green_reading(f"SYN-T{i+1:02d}") for i in range(3)], tick=0)
        t1 = [v for v in twin.active_violations if v.rule_id == "T1"]
        self.assertFalse(t1, "T1 must not fire with only 3 GREEN nodes")


# ---------------------------------------------------------------------------
# Finding 6: water_hammer leaves pump frozen after attack expiry
# ---------------------------------------------------------------------------

@unittest.skipIf(not _WNTR_OK, "wntr not installed")
class TestWaterHammerCleanup(unittest.TestCase):

    def setUp(self):
        from attacks import scenario_library
        scenario_library.reset_all()

    def test_pump_restored_to_original_status_after_expiry(self):
        import wntr
        from attacks import scenario_library

        original_status = wntr.network.LinkStatus.Open
        pump_10  = MagicMock()
        pump_10.initial_status  = original_status
        pump_335 = MagicMock()
        pump_335.initial_status = original_status

        def _get_link(pump_id):
            if pump_id == "10":  return pump_10
            if pump_id == "335": return pump_335
            return None

        mock_wn = MagicMock()
        mock_wn.pump_name_list = ["10", "335"]
        mock_wn.get_link = _get_link

        scenario_library.inject("water_hammer", tick=0, duration=4)
        for t in range(4):
            scenario_library.apply_attacks(t, mock_wn, None, {})
        # Tick 4: expired -- cleanup must restore original status
        scenario_library.apply_attacks(4, mock_wn, None, {})

        self.assertEqual(pump_10.initial_status,  original_status,
                         "pump_10 must be restored to Open after water_hammer expiry")
        self.assertEqual(pump_335.initial_status, original_status,
                         "pump_335 must be restored to Open after water_hammer expiry")


# ---------------------------------------------------------------------------
# Finding 8: _rolling_history not reset between simulation runs
# ---------------------------------------------------------------------------

class TestLayer2Reset(unittest.TestCase):

    def test_reset_function_exists(self):
        import layers.layer2_ingestion as l2
        self.assertTrue(hasattr(l2, "reset"), "layer2_ingestion must expose a reset() function")

    def test_reset_clears_rolling_history(self):
        import layers.layer2_ingestion as l2
        batch = {"tick": 0, "water": {"10": _pressure_raw("10", 35.0)}, "power": {}, "traffic": {}}
        process_batch(batch, {})
        self.assertGreater(len(l2._rolling_history), 0)
        l2.reset()
        self.assertEqual(len(l2._rolling_history), 0, "rolling history must be empty after reset()")


# ---------------------------------------------------------------------------
# Finding 10: DoS attack not applied to pump nodes
# ---------------------------------------------------------------------------

class TestDoSAppliedToPumpNodes(unittest.TestCase):

    def test_pump_nodes_dropped_under_dos(self):
        import random
        active_attacks = {"denial_of_service_ot": {"active": True}}
        water_batch = {f"pump_{i}": _pump_raw(str(i), 1.0) for i in range(20)}
        total = 0
        drops = 0
        random.seed(42)
        for _ in range(15):
            batch = {"tick": 0, "water": dict(water_batch), "power": {}, "traffic": {}}
            clean, _ = process_batch(batch, active_attacks)
            in_clean = sum(1 for r in clean if r.node_id.startswith("pump_"))
            total += 20
            drops += (20 - in_clean)
        drop_rate = drops / total
        self.assertGreater(drop_rate, 0.5,
                           f"Pump drop rate under DoS must be >50%, got {drop_rate:.0%}")

    def test_pump_nodes_not_dropped_without_dos(self):
        batch = {
            "tick": 0,
            "water": {f"pump_{i}": _pump_raw(str(i), 1.0) for i in range(5)},
            "power": {}, "traffic": {},
        }
        clean, _ = process_batch(batch, {})
        pump_count = sum(1 for r in clean if r.node_id.startswith("pump_"))
        self.assertEqual(pump_count, 5)


# ---------------------------------------------------------------------------
# Finding 11: IsoForest feature contamination by pump binary values
# ---------------------------------------------------------------------------

class TestIsoForestExcludesPumpStatus(unittest.TestCase):

    def setUp(self):
        isolation_forest.reset()

    def test_only_pump_readings_yield_none_vector(self):
        """Feature vector must be None when only pump_status nodes are present."""
        vec = isolation_forest._build_feature_vector(
            [_pump_reading("pump_10", 1.0), _pump_reading("pump_335", 0.0)]
        )
        self.assertIsNone(vec, "Feature vector must be None when only pump_status nodes present")

    def test_pressure_nodes_still_included(self):
        """Pressure readings must still appear in the feature vector."""
        vec = isolation_forest._build_feature_vector(
            [_pressure_reading("10", 35.0), _pump_reading("pump_10", 1.0)]
        )
        self.assertIsNotNone(vec)
        self.assertEqual(len(vec), 1, "Only the pressure node must be in the vector")


# ---------------------------------------------------------------------------
# Finding 13: W3 sentinel -1 causes spurious toggle
# ---------------------------------------------------------------------------

class TestW3SentinelNone(unittest.TestCase):

    def test_no_spurious_w3_when_pump_value_absent_then_zero(self):
        """Tick 0: pump state has no 'value'. Tick 1: value=0.0. No W3 toggle must fire."""
        twin = DigitalTwin()

        def _no_value_state(node_id):
            return {
                "node_id": node_id, "subsystem": "water", "metric": "pump_status",
                "unit": "", "source": "SIMULATED", "protocol": "Modbus/TCP",
                "status": "NORMAL", "timestamp_iso": "2026-01-01T00:00:00+00:00",
            }

        twin.state["pump_10"]  = _no_value_state("pump_10")
        twin.state["pump_335"] = _no_value_state("pump_335")
        twin._run_physics_rules(tick=0)

        twin.state["pump_10"]["value"]  = 0.0
        twin.state["pump_335"]["value"] = 0.0
        twin.active_violations = []
        twin._run_physics_rules(tick=1)

        w3 = [v for v in twin.active_violations if v.rule_id == "W3"]
        self.assertFalse(w3, "W3 must not fire spuriously when pump appears after tick with no 'value'")


if __name__ == "__main__":
    unittest.main()
