"""
Human Approval Queue
Buffers high-confidence (but sub-auto-quarantine) defensive actions
for operator review before execution.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PendingAction:
    action_id: str
    tick: int
    node_id: str
    subsystem: str
    confidence: float
    threat_class: str
    recommended_response: str
    evidence_trace: str
    status: str = "PENDING"
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action_id":            self.action_id,
            "tick":                 self.tick,
            "node_id":              self.node_id,
            "subsystem":            self.subsystem,
            "confidence":           self.confidence,
            "threat_class":         self.threat_class,
            "recommended_response": self.recommended_response,
            "evidence_trace":       self.evidence_trace,
            "status":               self.status,
            "created_at":           self.created_at,
            "resolved_at":          self.resolved_at,
            "resolved_by":          self.resolved_by,
            "rejection_reason":     self.rejection_reason,
        }


class ApprovalQueue:
    def __init__(self, ttl_seconds: float = 300.0):
        self._actions: Dict[str, PendingAction] = {}
        self._ttl = ttl_seconds

    def enqueue(
        self,
        action_id: str,
        *,
        tick: int,
        node_id: str,
        subsystem: str,
        confidence: float,
        threat_class: str,
        recommended_response: str,
        evidence_trace: str,
    ) -> str:
        if action_id in self._actions:
            raise ValueError(f"Action ID '{action_id}' already exists in queue")
        self._actions[action_id] = PendingAction(
            action_id=action_id,
            tick=tick,
            node_id=node_id,
            subsystem=subsystem,
            confidence=confidence,
            threat_class=threat_class,
            recommended_response=recommended_response,
            evidence_trace=evidence_trace,
        )
        return action_id

    def get(self, action_id: str) -> PendingAction:
        if action_id not in self._actions:
            raise KeyError(f"Action '{action_id}' not found")
        return self._actions[action_id]

    def pending(self) -> List[PendingAction]:
        return [a for a in self._actions.values() if a.status == "PENDING"]

    def approved(self) -> List[PendingAction]:
        return [a for a in self._actions.values() if a.status == "APPROVED"]

    def approve(self, action_id: str, *, approved_by: str) -> PendingAction:
        action = self.get(action_id)
        if action.status != "PENDING":
            raise ValueError(
                f"Action '{action_id}' is already resolved (status={action.status})"
            )
        action.status = "APPROVED"
        action.resolved_by = approved_by
        action.resolved_at = time.time()
        return action

    def reject(
        self,
        action_id: str,
        *,
        rejected_by: str,
        reason: Optional[str] = None,
    ) -> PendingAction:
        action = self.get(action_id)
        if action.status != "PENDING":
            raise ValueError(
                f"Action '{action_id}' is already resolved (status={action.status})"
            )
        action.status = "REJECTED"
        action.resolved_by = rejected_by
        action.resolved_at = time.time()
        action.rejection_reason = reason
        return action

    def expire_stale(self) -> List[PendingAction]:
        now = time.time()
        expired = []
        for action in self._actions.values():
            if action.status == "PENDING" and (now - action.created_at) >= self._ttl:
                action.status = "EXPIRED"
                action.resolved_at = now
                expired.append(action)
        return expired

    def all_as_dicts(self) -> List[dict]:
        return [a.to_dict() for a in self._actions.values()]
