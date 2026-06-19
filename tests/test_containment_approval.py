"""
Ticket 6 — Human-in-the-Loop Containment Approval tests.
Verifies CONTAINMENT_MODE config, auto/semi/manual paths, and TTL expiry.
"""

import time
import pytest

import config
from layers.approval_queue import ApprovalQueue, PendingAction


@pytest.fixture
def queue():
    return ApprovalQueue(ttl_seconds=300.0)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestContainmentModeConfig:

    def test_containment_mode_constant_exists(self):
        assert hasattr(config, "CONTAINMENT_MODE")

    def test_containment_mode_is_valid(self):
        assert config.CONTAINMENT_MODE in ("auto", "semi", "manual")

    def test_containment_mode_default_is_semi(self):
        assert config.CONTAINMENT_MODE == "semi"


# ---------------------------------------------------------------------------
# ApprovalQueue basics
# ---------------------------------------------------------------------------

class TestApprovalQueueBasics:

    def test_enqueue_returns_action_id(self, queue):
        aid = queue.enqueue(
            "abc123", tick=1, node_id="J1", subsystem="water",
            confidence=0.85, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1 fired",
        )
        assert aid == "abc123"

    def test_pending_returns_enqueued_action(self, queue):
        queue.enqueue(
            "xyz", tick=2, node_id="bus_5", subsystem="power",
            confidence=0.80, threat_class="LOAD_REDISTRIBUTION",
            recommended_response="Inspect", evidence_trace="P1/P2",
        )
        pending = queue.pending()
        assert len(pending) == 1
        assert pending[0].action_id == "xyz"

    def test_approve_changes_status(self, queue):
        queue.enqueue(
            "a1", tick=3, node_id="J2", subsystem="water",
            confidence=0.78, threat_class="FALSE_DATA_INJECTION",
            recommended_response="Sandbox", evidence_trace="W2",
        )
        action = queue.approve("a1", approved_by="operator")
        assert action.status == "APPROVED"
        assert action.resolved_by == "operator"

    def test_reject_changes_status(self, queue):
        queue.enqueue(
            "r1", tick=4, node_id="J3", subsystem="water",
            confidence=0.76, threat_class="RECONNAISSANCE",
            recommended_response="Monitor", evidence_trace="sub-threshold",
        )
        action = queue.reject("r1", rejected_by="operator", reason="False alarm")
        assert action.status == "REJECTED"
        assert action.rejection_reason == "False alarm"

    def test_cannot_approve_already_resolved(self, queue):
        queue.enqueue(
            "dup", tick=5, node_id="J4", subsystem="water",
            confidence=0.81, threat_class="ACTUATOR_HIJACK",
            recommended_response="Quarantine", evidence_trace="W4",
        )
        queue.approve("dup", approved_by="op1")
        with pytest.raises(ValueError):
            queue.approve("dup", approved_by="op2")

    def test_duplicate_action_id_raises(self, queue):
        queue.enqueue(
            "same_id", tick=1, node_id="J1", subsystem="water",
            confidence=0.80, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1",
        )
        with pytest.raises(ValueError):
            queue.enqueue(
                "same_id", tick=2, node_id="J1", subsystem="water",
                confidence=0.80, threat_class="WATER_HAMMER",
                recommended_response="Monitor", evidence_trace="W1",
            )


# ---------------------------------------------------------------------------
# Auto-execute after TTL in semi mode
# ---------------------------------------------------------------------------

class TestSemiModeAutoExpiry:

    def test_pending_action_expires_after_ttl(self):
        q = ApprovalQueue(ttl_seconds=0.01)
        q.enqueue(
            "exp1", tick=1, node_id="J1", subsystem="water",
            confidence=0.80, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1",
        )
        time.sleep(0.05)
        expired = q.expire_stale()
        assert len(expired) == 1
        assert expired[0].status == "EXPIRED"

    def test_non_expired_action_stays_pending(self):
        q = ApprovalQueue(ttl_seconds=300.0)
        q.enqueue(
            "fresh", tick=1, node_id="J1", subsystem="water",
            confidence=0.80, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1",
        )
        expired = q.expire_stale()
        assert len(expired) == 0
        assert q.get("fresh").status == "PENDING"

    def test_expire_stale_does_not_affect_resolved(self):
        q = ApprovalQueue(ttl_seconds=0.01)
        q.enqueue(
            "resolved", tick=1, node_id="J1", subsystem="water",
            confidence=0.80, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1",
        )
        q.approve("resolved", approved_by="op")
        time.sleep(0.05)
        expired = q.expire_stale()
        assert len(expired) == 0
        assert q.get("resolved").status == "APPROVED"


# ---------------------------------------------------------------------------
# all_as_dicts serialization
# ---------------------------------------------------------------------------

class TestSerialisation:

    def test_all_as_dicts_returns_list(self, queue):
        assert isinstance(queue.all_as_dicts(), list)

    def test_all_as_dicts_has_expected_keys(self, queue):
        queue.enqueue(
            "s1", tick=1, node_id="J1", subsystem="water",
            confidence=0.80, threat_class="WATER_HAMMER",
            recommended_response="Monitor", evidence_trace="W1",
        )
        d = queue.all_as_dicts()[0]
        for key in ("action_id", "tick", "node_id", "subsystem", "confidence",
                    "threat_class", "recommended_response", "evidence_trace",
                    "status", "created_at"):
            assert key in d, f"Missing key: {key}"
