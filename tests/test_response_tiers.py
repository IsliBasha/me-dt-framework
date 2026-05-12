"""
Tests for ResponseTier classification and Layer 5 routing.
RED: all tests fail until layers/response_tiers.py is created and Layer 5 updated.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestResponseTierEnum(unittest.TestCase):
    def setUp(self):
        from layers.response_tiers import ResponseTier
        self.ResponseTier = ResponseTier

    def test_monitor_tier_exists(self):
        self.assertTrue(hasattr(self.ResponseTier, "MONITOR"))

    def test_sandbox_tier_exists(self):
        self.assertTrue(hasattr(self.ResponseTier, "SANDBOX"))

    def test_quarantine_tier_exists(self):
        self.assertTrue(hasattr(self.ResponseTier, "QUARANTINE"))

    def test_none_tier_exists(self):
        self.assertTrue(hasattr(self.ResponseTier, "NONE"))


class TestClassifyTier(unittest.TestCase):
    def setUp(self):
        from layers.response_tiers import classify_tier, ResponseTier
        self.classify_tier = classify_tier
        self.ResponseTier = ResponseTier

    def test_below_monitor_threshold_is_none(self):
        result = self.classify_tier(0.40)
        self.assertEqual(result, self.ResponseTier.NONE)

    def test_at_monitor_threshold_is_monitor(self):
        result = self.classify_tier(0.50)
        self.assertEqual(result, self.ResponseTier.MONITOR)

    def test_mid_monitor_range_is_monitor(self):
        result = self.classify_tier(0.62)
        self.assertEqual(result, self.ResponseTier.MONITOR)

    def test_just_below_alert_threshold_is_monitor(self):
        result = self.classify_tier(0.749)
        self.assertEqual(result, self.ResponseTier.MONITOR)

    def test_at_alert_threshold_is_sandbox(self):
        result = self.classify_tier(0.75)
        self.assertEqual(result, self.ResponseTier.SANDBOX)

    def test_mid_sandbox_range_is_sandbox(self):
        result = self.classify_tier(0.85)
        self.assertEqual(result, self.ResponseTier.SANDBOX)

    def test_just_below_auto_contain_is_sandbox(self):
        result = self.classify_tier(0.919)
        self.assertEqual(result, self.ResponseTier.SANDBOX)

    def test_at_auto_contain_threshold_is_quarantine(self):
        result = self.classify_tier(0.92)
        self.assertEqual(result, self.ResponseTier.QUARANTINE)

    def test_high_confidence_is_quarantine(self):
        result = self.classify_tier(0.99)
        self.assertEqual(result, self.ResponseTier.QUARANTINE)

    def test_exactly_zero_is_none(self):
        result = self.classify_tier(0.0)
        self.assertEqual(result, self.ResponseTier.NONE)


class TestLayer5RoutingMonitorTier(unittest.TestCase):
    """MONITOR tier (0.50-0.75): log only, no queue, no quarantine."""

    def _make_mode_a(self, confidence: float):
        from models.state_vector import ThreatAssessment
        return ThreatAssessment(
            tick=1,
            threat_class="false_data_injection",
            confidence=confidence,
            affected_subsystems=["water"],
            recommended_response="increase monitoring",
            evidence_trace="sensor deviation observed",
        )

    def _make_engine(self):
        from layers.approval_queue import ApprovalQueue
        from layers.layer5_response import ResponseEngine
        return ResponseEngine(approval_queue=ApprovalQueue())

    def _make_twin(self):
        twin = MagicMock()
        twin.state = {"node_1": {"subsystem": "water"}}
        twin.node_status = {"node_1": "UNDER_ATTACK"}
        return twin

    def test_monitor_confidence_does_not_enqueue(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.62)
        twin = self._make_twin()
        result = engine.process(1, mode_a, None, None, [], None, [], twin)
        self.assertIsNone(result.get("queued_action_id"))

    def test_monitor_confidence_does_not_quarantine(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.62)
        twin = self._make_twin()
        engine.process(1, mode_a, None, None, [], None, [], twin)
        twin.quarantine_node.assert_not_called()

    def test_monitor_confidence_emits_event_with_monitor_tier(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.62)
        twin = self._make_twin()
        result = engine.process(1, mode_a, None, None, [], None, [], twin)
        events = result.get("new_events", [])
        self.assertTrue(len(events) > 0)
        tiers = [e.get("tier") for e in events]
        self.assertIn("MONITOR", tiers)

    def test_below_monitor_threshold_emits_no_medt_event(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.40)
        twin = self._make_twin()
        result = engine.process(1, mode_a, None, None, [], None, [], twin)
        medt_events = [e for e in result.get("new_events", []) if e.get("source") == "ME-DT"]
        self.assertEqual(len(medt_events), 0)


class TestLayer5RoutingSandboxTier(unittest.TestCase):
    """SANDBOX tier (0.75-0.92): queue for human approval."""

    def _make_mode_a(self, confidence: float):
        from models.state_vector import ThreatAssessment
        return ThreatAssessment(
            tick=5,
            threat_class="water_hammer",
            confidence=confidence,
            affected_subsystems=["water"],
            recommended_response="isolate pump",
            evidence_trace="pressure spike detected",
        )

    def _make_engine(self):
        from layers.approval_queue import ApprovalQueue
        from layers.layer5_response import ResponseEngine
        return ResponseEngine(approval_queue=ApprovalQueue())

    def _make_twin(self):
        twin = MagicMock()
        twin.state = {"pump_1": {"subsystem": "water"}}
        twin.node_status = {"pump_1": "UNDER_ATTACK"}
        return twin

    def test_sandbox_confidence_enqueues_action(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.83)
        twin = self._make_twin()
        result = engine.process(5, mode_a, None, None, [], None, [], twin)
        self.assertIsNotNone(result.get("queued_action_id"))

    def test_sandbox_confidence_does_not_quarantine(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.83)
        twin = self._make_twin()
        engine.process(5, mode_a, None, None, [], None, [], twin)
        twin.quarantine_node.assert_not_called()

    def test_sandbox_event_has_sandbox_tier(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.83)
        twin = self._make_twin()
        result = engine.process(5, mode_a, None, None, [], None, [], twin)
        events = result.get("new_events", [])
        tiers = [e.get("tier") for e in events if e.get("source") == "ME-DT"]
        self.assertIn("SANDBOX", tiers)


class TestLayer5RoutingQuarantineTier(unittest.TestCase):
    """QUARANTINE tier (>=0.92): auto-act without human review."""

    def _make_mode_a(self, confidence: float):
        from models.state_vector import ThreatAssessment
        return ThreatAssessment(
            tick=10,
            threat_class="actuator_hijack",
            confidence=confidence,
            affected_subsystems=["water"],
            recommended_response="quarantine node",
            evidence_trace="confirmed actuator compromise",
        )

    def _make_engine(self):
        from layers.approval_queue import ApprovalQueue
        from layers.layer5_response import ResponseEngine
        return ResponseEngine(approval_queue=ApprovalQueue())

    def _make_twin(self):
        twin = MagicMock()
        twin.state = {"valve_5": {"subsystem": "water"}}
        twin.node_status = {"valve_5": "UNDER_ATTACK"}
        return twin

    def test_quarantine_confidence_does_not_enqueue(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.95)
        twin = self._make_twin()
        result = engine.process(10, mode_a, None, None, [], None, [], twin)
        self.assertIsNone(result.get("queued_action_id"))

    def test_quarantine_confidence_auto_quarantines(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.95)
        twin = self._make_twin()
        engine.process(10, mode_a, None, None, [], None, [], twin)
        twin.quarantine_node.assert_called_once()

    def test_quarantine_event_has_quarantine_tier(self):
        engine = self._make_engine()
        mode_a = self._make_mode_a(0.95)
        twin = self._make_twin()
        result = engine.process(10, mode_a, None, None, [], None, [], twin)
        events = result.get("new_events", [])
        tiers = [e.get("tier") for e in events if e.get("source") == "ME-DT"]
        self.assertIn("QUARANTINE", tiers)


if __name__ == "__main__":
    unittest.main()
