from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AttackScenarioDefinition:
    name: str
    display_name: str
    description: str
    severity: str
    simulator: str          # WNTR | pandapower | SYNTHETIC | LAYER2
    threat_class: str
    duration_ticks: int
    subsystems: List[str]


SCENARIO_DEFINITIONS = {
    "false_data_injection": AttackScenarioDefinition(
        name="false_data_injection",
        display_name="FALSE DATA INJECTION",
        description="Zeroes demand on 3 Net3 junctions — WNTR produces 0-demand readings while pressure rises",
        severity="HIGH",
        simulator="WNTR",
        threat_class="FALSE_DATA_INJECTION",
        duration_ticks=8,
        subsystems=["water"],
    ),
    "water_hammer": AttackScenarioDefinition(
        name="water_hammer",
        display_name="WATER HAMMER",
        description="Rapid pump cycling — WNTR produces real pressure transients",
        severity="HIGH",
        simulator="WNTR",
        threat_class="WATER_HAMMER",
        duration_ticks=8,
        subsystems=["water"],
    ),
    "load_redistribution": AttackScenarioDefinition(
        name="load_redistribution",
        display_name="LOAD REDISTRIBUTION",
        description="Disables line 5 in case33bw — pandapower produces real voltage drops and overloads",
        severity="CRITICAL",
        simulator="pandapower",
        threat_class="LOAD_REDISTRIBUTION",
        duration_ticks=8,
        subsystems=["power"],
    ),
    "false_data_injection_power": AttackScenarioDefinition(
        name="false_data_injection_power",
        display_name="FDI POWER (BDD)",
        description="Bad data injection on DC approximation — stealthy load measurement manipulation",
        severity="HIGH",
        simulator="pandapower",
        threat_class="FALSE_DATA_INJECTION",
        duration_ticks=8,
        subsystems=["power"],
    ),
    "scada_replay": AttackScenarioDefinition(
        name="scada_replay",
        display_name="SCADA REPLAY",
        description="Restores stale topology snapshot — pandapower re-runs with stale state",
        severity="HIGH",
        simulator="pandapower",
        threat_class="SCADA_REPLAY",
        duration_ticks=8,
        subsystems=["power"],
    ),
    "cross_domain_cascade": AttackScenarioDefinition(
        name="cross_domain_cascade",
        display_name="CROSS-DOMAIN CASCADE",
        description="Traffic signal manipulation then power demand surge — real cross-domain effects",
        severity="CRITICAL",
        simulator="pandapower",
        threat_class="CROSS_DOMAIN_CASCADE",
        duration_ticks=12,
        subsystems=["traffic", "power"],
    ),
    "actuator_hijack": AttackScenarioDefinition(
        name="actuator_hijack",
        display_name="ACTUATOR HIJACK",
        description="Chlorine concentration spike in Net3 water quality simulation",
        severity="CRITICAL",
        simulator="WNTR",
        threat_class="ACTUATOR_HIJACK",
        duration_ticks=8,
        subsystems=["water"],
    ),
    "low_and_slow_recon": AttackScenarioDefinition(
        name="low_and_slow_recon",
        display_name="LOW-AND-SLOW RECON",
        description="Sub-threshold perturbations across water+power — designed to evade CUSUM h=5",
        severity="MEDIUM",
        simulator="WNTR",
        threat_class="RECONNAISSANCE",
        duration_ticks=20,
        subsystems=["water", "power"],
    ),
    "denial_of_service_ot": AttackScenarioDefinition(
        name="denial_of_service_ot",
        display_name="DENIAL OF SERVICE OT",
        description="80% packet drop on water subsystem — MISSING events flood anomaly sidecar",
        severity="HIGH",
        simulator="LAYER2",
        threat_class="DENIAL_OF_SERVICE_OT",
        duration_ticks=8,
        subsystems=["water"],
    ),
}
