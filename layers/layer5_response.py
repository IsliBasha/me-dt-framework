"""
Layer 5 — Alert, Response, and Metrics Integration
Processes ME-DT threat assessments, CUSUM/IsoForest alerts,
decides on auto-containment, and emits alert events.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from models.state_vector import (
    ThreatAssessment, AttackPath, ZeroDayHypothesis,
    CUSUMAlert, IsoForestAlert, AlertEvent,
)
from models.threat_model import THREAT_LEVEL_MAP
from layers.approval_queue import ApprovalQueue
from layers.response_tiers import ResponseTier, classify_tier


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _threat_level(confidence: float) -> str:
    if confidence >= 0.90:
        return "CRITICAL"
    if confidence >= 0.75:
        return "HIGH"
    if confidence >= 0.50:
        return "MEDIUM"
    if confidence >= 0.25:
        return "LOW"
    return "NONE"


class ResponseEngine:
    def __init__(self, approval_queue: Optional[ApprovalQueue] = None):
        self.alert_log: List[AlertEvent] = []
        self.auto_contained: List[str] = []
        self._queue: ApprovalQueue = approval_queue or ApprovalQueue()

    def process(
        self,
        tick: int,
        mode_a: Optional[ThreatAssessment],
        mode_b_raw: Optional[Dict],
        mode_c: Optional[List[ZeroDayHypothesis]],
        cusum_alerts: List[CUSUMAlert],
        isoforest_alert: Optional[IsoForestAlert],
        violations: List[Dict],
        twin,
        wn=None,
        net=None,
    ) -> Dict:
        events: List[AlertEvent] = []
        queued_action_id: Optional[str] = None

        # --- ME-DT Mode A ---
        threat_level = "NONE"
        if mode_a:
            tier = classify_tier(mode_a.confidence)

            if tier != ResponseTier.NONE:
                tl = _threat_level(mode_a.confidence)
                threat_level = tl
                actions = [mode_a.recommended_response]

                if tier == ResponseTier.QUARANTINE:
                    for subsystem in mode_a.affected_subsystems:
                        candidates = [
                            nid for nid, nd in twin.state.items()
                            if nd.get("subsystem") == subsystem
                            and twin.node_status.get(nid, "NORMAL") == "UNDER_ATTACK"
                        ][:1]
                        for nid in candidates:
                            twin.quarantine_node(nid, wn, net)
                            actions.append(f"AUTO-QUARANTINE: {nid}")
                            self.auto_contained.append(nid)

                elif tier == ResponseTier.SANDBOX:
                    action_id = str(uuid.uuid4())[:8]
                    self._queue.enqueue(
                        action_id,
                        tick=tick,
                        node_id=mode_a.affected_subsystems[0] if mode_a.affected_subsystems else "unknown",
                        subsystem=mode_a.affected_subsystems[0] if mode_a.affected_subsystems else "unknown",
                        confidence=mode_a.confidence,
                        threat_class=mode_a.threat_class,
                        recommended_response=mode_a.recommended_response,
                        evidence_trace=mode_a.evidence_trace,
                    )
                    queued_action_id = action_id
                    actions.append(f"QUEUED-FOR-APPROVAL: {action_id}")

                # MONITOR tier: log only, no queue, no quarantine

                ev = AlertEvent(
                    alert_id=str(uuid.uuid4())[:8],
                    tick=tick,
                    timestamp_iso=_iso_now(),
                    source="ME-DT",
                    severity=tl,
                    threat_class=mode_a.threat_class,
                    confidence=mode_a.confidence,
                    affected_nodes=[],
                    response_actions=actions,
                    message=mode_a.evidence_trace,
                    tier=tier.value,
                )
                events.append(ev)
                self.alert_log.append(ev)

        # Physics violation-based threat level
        if violations:
            severities = [v.get("severity", "LOW") for v in violations]
            sev_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            max_sev = max(severities, key=lambda s: sev_order.get(s, 0))
            if sev_order.get(max_sev, 0) > sev_order.get(threat_level, 0):
                threat_level = max_sev

        # --- CUSUM alerts ---
        for ca in cusum_alerts:
            ev = AlertEvent(
                alert_id=str(uuid.uuid4())[:8],
                tick=tick,
                timestamp_iso=_iso_now(),
                source="CUSUM",
                severity="MEDIUM",
                threat_class=None,
                confidence=None,
                affected_nodes=[ca.node_id],
                response_actions=["Monitor node"],
                message=f"CUSUM {ca.direction} alert: node={ca.node_id} acc={ca.accumulator_value:.2f}",
            )
            events.append(ev)
            self.alert_log.append(ev)

        # --- IsoForest alert ---
        if isoforest_alert:
            ev = AlertEvent(
                alert_id=str(uuid.uuid4())[:8],
                tick=tick,
                timestamp_iso=_iso_now(),
                source="ISOFOREST",
                severity="MEDIUM",
                threat_class=None,
                confidence=None,
                affected_nodes=[],
                response_actions=["Review feature vector"],
                message=f"IsoForest anomaly score={isoforest_alert.anomaly_score:.4f}",
            )
            events.append(ev)
            self.alert_log.append(ev)

        # Expire stale pending actions each tick
        self._queue.expire_stale()

        return {
            "threat_level":     threat_level,
            "new_events":       [_alert_to_dict(e) for e in events],
            "queued_action_id": queued_action_id,
            "mode_b":           mode_b_raw,
            "mode_c":           [
                {
                    "rank":                     h.rank,
                    "attack_class":             h.attack_class,
                    "attacker_intent":          h.attacker_intent,
                    "physical_impact_severity": h.physical_impact_severity,
                    "why_standard_ids_misses":  h.why_standard_ids_misses,
                    "recommended_monitoring":   h.recommended_monitoring,
                }
                for h in (mode_c or [])
            ],
        }

    def get_recent_events(self, n: int = 50) -> List[Dict]:
        return [_alert_to_dict(e) for e in self.alert_log[-n:]]


def _alert_to_dict(e: AlertEvent) -> Dict:
    return {
        "alert_id":       e.alert_id,
        "tick":           e.tick,
        "timestamp_iso":  e.timestamp_iso,
        "source":         e.source,
        "severity":       e.severity,
        "threat_class":   e.threat_class,
        "confidence":     e.confidence,
        "affected_nodes": e.affected_nodes,
        "response_actions": e.response_actions,
        "message":        e.message,
        "tier":           e.tier,
    }
