from dataclasses import dataclass, field
from typing import List, Optional


THREAT_TAXONOMY = [
    "SIGNAL_MANIPULATION",
    "LOAD_REDISTRIBUTION",
    "WATER_HAMMER",
    "FALSE_DATA_INJECTION",
    "SCADA_REPLAY",
    "DENIAL_OF_SERVICE_OT",
    "CROSS_DOMAIN_CASCADE",
    "RECONNAISSANCE",
    "ACTUATOR_HIJACK",
    "SUPPLY_CHAIN_COMPROMISE",
    "UNKNOWN",
    "NONE",
]

SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

THREAT_LEVEL_MAP = {
    "NONE":     "NONE",
    "LOW":      "LOW",
    "MEDIUM":   "MEDIUM",
    "HIGH":     "HIGH",
    "CRITICAL": "CRITICAL",
}


@dataclass
class VulnerabilityAtlasEntry:
    entry_point: str
    detection_difficulty: str
    estimated_impact_severity: int
    evasion_rationale: str
    tick_discovered: int


@dataclass
class ThreatSchema:
    threat_class: str
    description: str
    affected_subsystems: List[str]
    typical_indicators: List[str]
    severity: str
    detection_difficulty: str


KNOWN_THREATS: List[ThreatSchema] = [
    ThreatSchema(
        "WATER_HAMMER",
        "Rapid pump cycling causing hydraulic pressure transients",
        ["water"],
        ["RAPID_PUMP_CYCLING", "pressure oscillation", "flow_surge"],
        "HIGH",
        "MEDIUM",
    ),
    ThreatSchema(
        "FALSE_DATA_INJECTION",
        "Manipulation of sensor readings to hide attack or cause wrong responses",
        ["water", "power"],
        ["hash mismatch", "zero demand anomaly", "voltage inconsistency"],
        "HIGH",
        "HIGH",
    ),
    ThreatSchema(
        "LOAD_REDISTRIBUTION",
        "Disabling power lines to force dangerous load redistribution",
        ["power"],
        ["LINE_OVERLOAD", "VOLTAGE_VIOLATION", "cascade"],
        "CRITICAL",
        "LOW",
    ),
    ThreatSchema(
        "DENIAL_OF_SERVICE_OT",
        "Flooding or dropping OT protocol packets to cause MISSING events",
        ["water"],
        ["MISSING nodes", "packet drop", "communication loss"],
        "HIGH",
        "LOW",
    ),
    ThreatSchema(
        "CROSS_DOMAIN_CASCADE",
        "Coordinated attack across multiple infrastructure domains",
        ["traffic", "power", "water"],
        ["CROSS_DOMAIN_CORRELATION", "INFRASTRUCTURE_STRESS"],
        "CRITICAL",
        "HIGH",
    ),
    ThreatSchema(
        "RECONNAISSANCE",
        "Low-amplitude probing to map system response without triggering thresholds",
        ["water", "power"],
        ["sub-threshold perturbations", "systematic scanning"],
        "MEDIUM",
        "HIGH",
    ),
    ThreatSchema(
        "SCADA_REPLAY",
        "Replaying stale SCADA commands to restore outdated topology",
        ["power"],
        ["topology mismatch", "stale tap positions", "load mismatch"],
        "HIGH",
        "HIGH",
    ),
    ThreatSchema(
        "ACTUATOR_HIJACK",
        "Unauthorized modification of actuator setpoints (e.g., chlorine dosing)",
        ["water"],
        ["ACTUATOR_OVERRIDE", "chemical concentration spike"],
        "CRITICAL",
        "MEDIUM",
    ),
]
