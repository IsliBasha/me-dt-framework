"""
TDD: Human Approval Queue
Tests for the ApprovalQueue class and the Layer 5 routing logic.
All tests written before implementation — RED gate.
"""
import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layers.approval_queue import ApprovalQueue, PendingAction


# ---------------------------------------------------------------------------
# PendingAction model
# ---------------------------------------------------------------------------

class TestPendingAction(unittest.TestCase):

    def test_pending_action_has_required_fields(self):
        action = PendingAction(
            action_id="abc123",
            tick=5,
            node_id="pump_10",
            subsystem="water",
            confidence=0.85,
            threat_class="WATER_HAMMER",
            recommended_response="Close pump_10 isolation valve",
            evidence_trace="W1+W3 violations on pump_10; pressure transient 12m above baseline",
        )
        self.assertEqual(action.action_id, "abc123")
        self.assertEqual(action.node_id, "pump_10")
        self.assertEqual(action.status, "PENDING")

    def test_pending_action_default_status_is_pending(self):
        action = PendingAction(
            action_id="x",
            tick=1,
            node_id="bus_0",
            subsystem="power",
            confidence=0.80,
            threat_class="LOAD_REDISTRIBUTION",
            recommended_response="Trip bus_0",
            evidence_trace="P1 voltage violation",
        )
        self.assertEqual(action.status, "PENDING")

    def test_pending_action_created_at_is_set(self):
        before = time.time()
        action = PendingAction(
            action_id="y",
            tick=2,
            node_id="10",
            subsystem="water",
            confidence=0.78,
            threat_class="FALSE_DATA_INJECTION",
            recommended_response="Isolate node 10",
            evidence_trace="W2 pressure underflow",
        )
        after = time.time()
        self.assertGreaterEqual(action.created_at, before)
        self.assertLessEqual(action.created_at, after)


# ---------------------------------------------------------------------------
# ApprovalQueue — enqueue
# ---------------------------------------------------------------------------

class TestApprovalQueueEnqueue(unittest.TestCase):

    def setUp(self):
        self.q = ApprovalQueue()

    def test_enqueue_adds_action_to_pending(self):
        self.q.enqueue("a1", tick=1, node_id="pump_10", subsystem="water",
                       confidence=0.80, threat_class="WATER_HAMMER",
                       recommended_response="Close valve",
                       evidence_trace="W3 pump cycling")
        self.assertEqual(len(self.q.pending()), 1)

    def test_enqueue_returns_action_id(self):
        aid = self.q.enqueue("a2", tick=1, node_id="bus_0", subsystem="power",
                              confidence=0.82, threat_class="LOAD_REDISTRIBUTION",
                              recommended_response="Trip breaker",
                              evidence_trace="P1 voltage")
        self.assertEqual(aid, "a2")

    def test_enqueue_duplicate_id_raises(self):
        self.q.enqueue("dup", tick=1, node_id="pump_10", subsystem="water",
                       confidence=0.80, threat_class="WATER_HAMMER",
                       recommended_response="x", evidence_trace="y")
        with self.assertRaises(ValueError):
            self.q.enqueue("dup", tick=2, node_id="pump_10", subsystem="water",
                           confidence=0.81, threat_class="WATER_HAMMER",
                           recommended_response="x", evidence_trace="y")

    def test_pending_returns_only_pending_actions(self):
        self.q.enqueue("p1", tick=1, node_id="n1", subsystem="water",
                       confidence=0.80, threat_class="T", recommended_response="r",
                       evidence_trace="e")
        self.q.enqueue("p2", tick=2, node_id="n2", subsystem="water",
                       confidence=0.81, threat_class="T", recommended_response="r",
                       evidence_trace="e")
        self.q.approve("p1", approved_by="operator")
        pending = self.q.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].action_id, "p2")


# ---------------------------------------------------------------------------
# ApprovalQueue — approve
# ---------------------------------------------------------------------------

class TestApprovalQueueApprove(unittest.TestCase):

    def setUp(self):
        self.q = ApprovalQueue()
        self.q.enqueue("act1", tick=3, node_id="pump_10", subsystem="water",
                       confidence=0.85, threat_class="WATER_HAMMER",
                       recommended_response="Close pump_10 valve",
                       evidence_trace="W1+W3")

    def test_approve_changes_status_to_approved(self):
        self.q.approve("act1", approved_by="operator")
        action = self.q.get("act1")
        self.assertEqual(action.status, "APPROVED")

    def test_approve_records_who_approved(self):
        self.q.approve("act1", approved_by="senior_operator")
        action = self.q.get("act1")
        self.assertEqual(action.resolved_by, "senior_operator")

    def test_approve_sets_resolved_at(self):
        before = time.time()
        self.q.approve("act1", approved_by="op")
        after = time.time()
        action = self.q.get("act1")
        self.assertGreaterEqual(action.resolved_at, before)
        self.assertLessEqual(action.resolved_at, after)

    def test_approve_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.q.approve("no-such-id", approved_by="op")

    def test_approve_already_resolved_raises(self):
        self.q.approve("act1", approved_by="op")
        with self.assertRaises(ValueError):
            self.q.approve("act1", approved_by="op2")

    def test_approved_actions_in_approved_list(self):
        self.q.approve("act1", approved_by="op")
        approved = self.q.approved()
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].action_id, "act1")


# ---------------------------------------------------------------------------
# ApprovalQueue — reject
# ---------------------------------------------------------------------------

class TestApprovalQueueReject(unittest.TestCase):

    def setUp(self):
        self.q = ApprovalQueue()
        self.q.enqueue("act2", tick=4, node_id="bus_4", subsystem="power",
                       confidence=0.78, threat_class="LOAD_REDISTRIBUTION",
                       recommended_response="Trip bus_4",
                       evidence_trace="P2 overload")

    def test_reject_changes_status_to_rejected(self):
        self.q.reject("act2", rejected_by="operator", reason="False positive suspected")
        action = self.q.get("act2")
        self.assertEqual(action.status, "REJECTED")

    def test_reject_records_reason(self):
        self.q.reject("act2", rejected_by="op", reason="Planned maintenance")
        action = self.q.get("act2")
        self.assertEqual(action.rejection_reason, "Planned maintenance")

    def test_reject_reason_optional(self):
        self.q.reject("act2", rejected_by="op")
        action = self.q.get("act2")
        self.assertIsNone(action.rejection_reason)

    def test_reject_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.q.reject("no-such-id", rejected_by="op")

    def test_reject_already_resolved_raises(self):
        self.q.reject("act2", rejected_by="op", reason="FP")
        with self.assertRaises(ValueError):
            self.q.reject("act2", rejected_by="op2", reason="again")

    def test_rejected_actions_not_in_pending(self):
        self.q.reject("act2", rejected_by="op")
        self.assertEqual(len(self.q.pending()), 0)


# ---------------------------------------------------------------------------
# ApprovalQueue — expiry
# ---------------------------------------------------------------------------

class TestApprovalQueueExpiry(unittest.TestCase):

    def test_expire_removes_stale_pending_actions(self):
        q = ApprovalQueue(ttl_seconds=0.05)
        q.enqueue("exp1", tick=1, node_id="n1", subsystem="water",
                  confidence=0.80, threat_class="T",
                  recommended_response="r", evidence_trace="e")
        time.sleep(0.1)
        expired = q.expire_stale()
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0].action_id, "exp1")
        self.assertEqual(expired[0].status, "EXPIRED")
        self.assertEqual(len(q.pending()), 0)

    def test_expire_does_not_remove_fresh_actions(self):
        q = ApprovalQueue(ttl_seconds=60)
        q.enqueue("fresh", tick=1, node_id="n1", subsystem="water",
                  confidence=0.80, threat_class="T",
                  recommended_response="r", evidence_trace="e")
        expired = q.expire_stale()
        self.assertEqual(len(expired), 0)
        self.assertEqual(len(q.pending()), 1)

    def test_expire_does_not_affect_already_resolved_actions(self):
        q = ApprovalQueue(ttl_seconds=0.05)
        q.enqueue("res1", tick=1, node_id="n1", subsystem="water",
                  confidence=0.80, threat_class="T",
                  recommended_response="r", evidence_trace="e")
        q.approve("res1", approved_by="op")
        time.sleep(0.1)
        expired = q.expire_stale()
        self.assertEqual(len(expired), 0)


# ---------------------------------------------------------------------------
# Layer 5 routing: queue vs auto-contain
# ---------------------------------------------------------------------------

class TestLayer5Routing(unittest.TestCase):
    """
    Layer 5 ResponseEngine must route actions to the approval queue
    when confidence is in [ALERT_THRESHOLD, AUTO_CONTAIN_THRESHOLD)
    and auto-quarantine only when confidence >= AUTO_CONTAIN_THRESHOLD.
    """

    def setUp(self):
        import config
        from layers.layer5_response import ResponseEngine
        from layers.approval_queue import ApprovalQueue
        self.config = config
        self.ResponseEngine = ResponseEngine
        self.ApprovalQueue = ApprovalQueue

    def _make_mode_a(self, confidence, threat_class="WATER_HAMMER",
                     subsystems=None, response="Close valve", evidence="W1"):
        from models.state_vector import ThreatAssessment
        return ThreatAssessment(
            threat_class=threat_class,
            confidence=confidence,
            evidence_trace=evidence,
            affected_subsystems=subsystems or ["water"],
            physical_consequence="Physical damage possible",
            recommended_response=response,
            reasoning_chain="Chain of thought.",
            tick=1,
            api_latency_ms=50.0,
        )

    def test_high_confidence_below_auto_contain_goes_to_queue(self):
        """confidence=0.85 (>= 0.75, < 0.92) must enqueue, not auto-quarantine."""
        q = self.ApprovalQueue()
        engine = self.ResponseEngine(approval_queue=q)
        mode_a = self._make_mode_a(confidence=0.85)

        from unittest.mock import MagicMock
        twin = MagicMock()
        twin.state = {}
        twin.node_status = {}

        engine.process(tick=1, mode_a=mode_a, mode_b_raw=None, mode_c=None,
                       cusum_alerts=[], isoforest_alert=None,
                       violations=[], twin=twin)

        self.assertEqual(len(q.pending()), 1)
        twin.quarantine_node.assert_not_called()

    def test_critical_confidence_auto_quarantines_and_does_not_queue(self):
        """confidence=0.95 (>= 0.92) must auto-quarantine and not enqueue."""
        q = self.ApprovalQueue()
        engine = self.ResponseEngine(approval_queue=q)
        mode_a = self._make_mode_a(confidence=0.95, subsystems=["water"])

        from unittest.mock import MagicMock
        twin = MagicMock()
        twin.state = {"pump_10": {"subsystem": "water"}}
        twin.node_status = {"pump_10": "UNDER_ATTACK"}

        engine.process(tick=1, mode_a=mode_a, mode_b_raw=None, mode_c=None,
                       cusum_alerts=[], isoforest_alert=None,
                       violations=[], twin=twin)

        self.assertEqual(len(q.pending()), 0)
        twin.quarantine_node.assert_called_once()

    def test_below_alert_threshold_does_not_queue(self):
        """confidence=0.50 (< 0.75 ALERT_THRESHOLD) must not enqueue."""
        q = self.ApprovalQueue()
        engine = self.ResponseEngine(approval_queue=q)
        mode_a = self._make_mode_a(confidence=0.50)

        from unittest.mock import MagicMock
        twin = MagicMock()
        twin.state = {}
        twin.node_status = {}

        engine.process(tick=1, mode_a=mode_a, mode_b_raw=None, mode_c=None,
                       cusum_alerts=[], isoforest_alert=None,
                       violations=[], twin=twin)

        self.assertEqual(len(q.pending()), 0)

    def test_process_result_includes_queued_action_id(self):
        """Result dict must contain 'queued_action_id' when an action is enqueued."""
        q = self.ApprovalQueue()
        engine = self.ResponseEngine(approval_queue=q)
        mode_a = self._make_mode_a(confidence=0.85)

        from unittest.mock import MagicMock
        twin = MagicMock()
        twin.state = {}
        twin.node_status = {}

        result = engine.process(tick=1, mode_a=mode_a, mode_b_raw=None, mode_c=None,
                                cusum_alerts=[], isoforest_alert=None,
                                violations=[], twin=twin)

        self.assertIn("queued_action_id", result)
        self.assertIsNotNone(result["queued_action_id"])


if __name__ == "__main__":
    unittest.main()
