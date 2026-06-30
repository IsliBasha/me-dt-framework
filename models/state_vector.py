from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class NodeReading:
    node_id: str
    subsystem: str          # water | power | traffic
    metric: str
    value: float
    unit: str
    protocol: str
    timestamp_iso: str
    timestamp_ms: int
    confidence: float
    source: str             # SIMULATED | SYNTHETIC
    integrity_hash: str
    status: str = "NORMAL"  # NORMAL | SUSPECT | QUARANTINED | UNDER_ATTACK
    signal_phase: Optional[str] = None


@dataclass
class AnomalyEvent:
    node_id: str
    subsystem: str
    event_type: str         # SUSPECT | MISSING
    value: Optional[float]
    rolling_mean: Optional[float]
    rolling_std: Optional[float]
    tick: int
    timestamp_iso: str


@dataclass
class PhysicsViolationEvent:
    rule_id: str
    description: str
    affected_nodes: List[str]
    subsystem: str
    severity: str           # LOW | MEDIUM | HIGH | CRITICAL
    tick: int
    timestamp_iso: str
    cross_domain: bool = False
    traffic_model: Optional[str] = None


@dataclass
class ThreatAssessment:
    threat_class: str
    confidence: float
    evidence_trace: str
    affected_subsystems: List[str]
    physical_consequence: str
    recommended_response: str
    reasoning_chain: str
    tick: int
    api_latency_ms: float


@dataclass
class AttackStep:
    step: int
    action: str
    target_node: str
    expected_effect: str


@dataclass
class AttackPath:
    entry_point: str
    attack_steps: List[AttackStep]
    physical_consequence: str
    detection_difficulty: str   # LOW | MEDIUM | HIGH
    evasion_rationale: str
    estimated_impact_severity: int
    tick: int


@dataclass
class ZeroDayHypothesis:
    rank: int
    attack_class: str
    attacker_intent: str
    physical_impact_severity: int
    why_standard_ids_misses: str
    recommended_monitoring: str


@dataclass
class CUSUMAlert:
    node_id: str
    direction: str          # HIGH | LOW
    tick: int
    value: float
    accumulator_value: float


@dataclass
class IsoForestAlert:
    tick: int
    anomaly_score: float
    feature_vector_norm: float


@dataclass
class AlertEvent:
    alert_id: str
    tick: int
    timestamp_iso: str
    source: str             # ME-DT | CUSUM | ISOFOREST
    severity: str
    threat_class: Optional[str]
    confidence: Optional[float]
    affected_nodes: List[str]
    response_actions: List[str]
    message: str
    tier: Optional[str] = None


@dataclass
class SimulationMetrics:
    me_dt: Dict[str, Any] = field(default_factory=dict)
    cusum: Dict[str, Any] = field(default_factory=dict)
    isoforest: Dict[str, Any] = field(default_factory=dict)
