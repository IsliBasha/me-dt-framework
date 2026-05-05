"""
Ticket #4: denial_of_service_ot button presence and Layer 2 integration.
The attack now exists in all three places (SCENARIO_DEFINITIONS, dashboard.js,
scenario_library). These tests are regression guards for the full pipeline.
"""
import re
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.layer2_ingestion import process_batch
from models.attack_scenarios import SCENARIO_DEFINITIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DASHBOARD_JS = os.path.join(os.path.dirname(__file__), "..", "static", "js", "dashboard.js")

_ALL_SCENARIO_NAMES = list(SCENARIO_DEFINITIONS.keys())

_EXPECTED_SCENARIOS = {
    "false_data_injection",
    "water_hammer",
    "load_redistribution",
    "false_data_injection_power",
    "scada_replay",
    "cross_domain_cascade",
    "actuator_hijack",
    "low_and_slow_recon",
    "denial_of_service_ot",
}


def _water_batch(node_ids: list, tick: int = 0) -> dict:
    nodes = {}
    for nid in node_ids:
        nodes[nid] = {
            "pressure":      35.0,
            "unit":          "m",
            "status":        "NORMAL",
            "subsystem":     "water",
            "source":        "SIMULATED",
            "timestamp_ms":  0,
            "timestamp_iso": "2026-01-01T00:00:00+00:00",
            "integrity_hash": "",
        }
    return {"tick": tick, "water": nodes, "power": {}, "traffic": {}}


def _dos_active_attack_state() -> dict:
    return {"denial_of_service_ot": {"active": True}}


def _extract_dashboard_attack_names() -> set:
    """Parse the ATTACKS array from dashboard.js and return all name values."""
    with open(_DASHBOARD_JS, encoding="utf-8") as f:
        src = f.read()
    return set(re.findall(r"name:'([^']+)'", src))


# ---------------------------------------------------------------------------
# Metadata synchrony tests
# ---------------------------------------------------------------------------

class TestScenarioDefinitionsSync(unittest.TestCase):

    def test_denial_of_service_ot_in_scenario_definitions(self):
        """SCENARIO_DEFINITIONS must include denial_of_service_ot."""
        self.assertIn("denial_of_service_ot", SCENARIO_DEFINITIONS)

    def test_all_nine_scenarios_defined(self):
        """All 9 scenarios must be present in SCENARIO_DEFINITIONS."""
        self.assertEqual(set(SCENARIO_DEFINITIONS.keys()), _EXPECTED_SCENARIOS)

    def test_denial_of_service_ot_metadata(self):
        """denial_of_service_ot definition must have correct severity and simulator."""
        defn = SCENARIO_DEFINITIONS["denial_of_service_ot"]
        self.assertEqual(defn.severity, "HIGH")
        self.assertEqual(defn.simulator, "LAYER2")
        self.assertIn("water", defn.subsystems)

    def test_dashboard_js_contains_denial_of_service_ot(self):
        """dashboard.js ATTACKS array must include denial_of_service_ot."""
        names = _extract_dashboard_attack_names()
        self.assertIn("denial_of_service_ot", names)

    def test_dashboard_js_attacks_match_scenario_definitions(self):
        """Every scenario in SCENARIO_DEFINITIONS must have a button in dashboard.js."""
        names = _extract_dashboard_attack_names()
        for scenario in _EXPECTED_SCENARIOS:
            self.assertIn(scenario, names,
                          msg=f"'{scenario}' missing from dashboard.js ATTACKS array")

    def test_dashboard_js_has_no_unknown_attacks(self):
        """dashboard.js ATTACKS array must not contain names absent from SCENARIO_DEFINITIONS."""
        names = _extract_dashboard_attack_names()
        for name in names:
            self.assertIn(name, _EXPECTED_SCENARIOS,
                          msg=f"'{name}' in dashboard.js but not in SCENARIO_DEFINITIONS")


# ---------------------------------------------------------------------------
# Layer 2 DoS packet-drop behaviour tests
# ---------------------------------------------------------------------------

class TestDoSLayer2Behaviour(unittest.TestCase):

    def test_dos_drops_all_water_packets_when_random_always_low(self):
        """With random=0.0 (always below 0.80 threshold), all water nodes become MISSING."""
        batch = _water_batch(["10", "15", "20", "35"])
        with patch("random.random", return_value=0.0):
            _, anomalies = process_batch(batch, _dos_active_attack_state())
        missing = [a for a in anomalies if a.event_type == "MISSING"]
        self.assertEqual(len(missing), 4,
                         "All 4 water nodes should be dropped as MISSING")

    def test_dos_drops_no_packets_when_random_always_high(self):
        """With random=0.99 (above 0.80 threshold), no water nodes are dropped."""
        batch = _water_batch(["10", "15", "20"])
        with patch("random.random", return_value=0.99):
            clean, anomalies = process_batch(batch, _dos_active_attack_state())
        missing = [a for a in anomalies if a.event_type == "MISSING"]
        self.assertEqual(len(missing), 0,
                         "No nodes should be dropped when random > 0.80")
        self.assertEqual(len([r for r in clean if r.subsystem == "water"]), 3)

    def test_dos_inactive_passes_all_water_packets(self):
        """Without DoS in attack_state, all water nodes pass through to clean_stream."""
        batch = _water_batch(["10", "15", "20"])
        clean, anomalies = process_batch(batch, {})
        water_readings = [r for r in clean if r.subsystem == "water"]
        missing = [a for a in anomalies if a.event_type == "MISSING"]
        self.assertEqual(len(water_readings), 3)
        self.assertEqual(len(missing), 0)

    def test_dos_does_not_drop_power_packets(self):
        """DoS must only affect water — power nodes must always pass through."""
        batch = {
            "tick": 0,
            "water": {"10": {"pressure": 35.0, "unit": "m", "status": "NORMAL",
                              "subsystem": "water", "source": "SIMULATED",
                              "timestamp_ms": 0, "timestamp_iso": "2026-01-01T00:00:00+00:00",
                              "integrity_hash": ""}},
            "power": {"0": {"vm_pu": 1.0, "unit": "pu", "status": "NORMAL",
                             "subsystem": "power", "source": "SIMULATED",
                             "timestamp_ms": 0, "timestamp_iso": "2026-01-01T00:00:00+00:00",
                             "integrity_hash": ""}},
            "traffic": {},
        }
        with patch("random.random", return_value=0.0):
            clean, _ = process_batch(batch, _dos_active_attack_state())
        power_nodes = [r for r in clean if r.subsystem == "power"]
        self.assertEqual(len(power_nodes), 1,
                         "Power nodes must not be dropped by DoS")

    def test_dos_missing_event_has_correct_fields(self):
        """MISSING anomaly events must have subsystem=water, value=None, rolling fields=None."""
        batch = _water_batch(["10"])
        with patch("random.random", return_value=0.0):
            _, anomalies = process_batch(batch, _dos_active_attack_state())
        self.assertEqual(len(anomalies), 1)
        ev = anomalies[0]
        self.assertEqual(ev.event_type, "MISSING")
        self.assertEqual(ev.subsystem, "water")
        self.assertEqual(ev.node_id, "10")
        self.assertIsNone(ev.value)
        self.assertIsNone(ev.rolling_mean)
        self.assertIsNone(ev.rolling_std)


if __name__ == "__main__":
    unittest.main()
