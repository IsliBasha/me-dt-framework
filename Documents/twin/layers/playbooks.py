"""
Per-threat-class playbooks — ordered action sequences executed on QUARANTINE tier.
Each playbook is a list of PlaybookStep objects keyed by threat class (lowercase).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlaybookStep:
    action_type: str
    description: str
    params: Dict[str, Any] = field(default_factory=dict)


PLAYBOOKS: Dict[str, List[PlaybookStep]] = {
    "water_hammer": [
        PlaybookStep(
            action_type="close_valve",
            description="Shut downstream valve to arrest pressure wave",
            params={"target": "downstream_valve"},
        ),
        PlaybookStep(
            action_type="wait",
            description="Hold for 3 ticks to let transient dissipate",
            params={"ticks": 3},
        ),
        PlaybookStep(
            action_type="verify_pressure",
            description="Confirm pressure returned to baseline range",
            params={"tolerance_m": 2.0},
        ),
    ],
    "load_redistribution": [
        PlaybookStep(
            action_type="shed_load",
            description="Drop non-critical loads on affected bus to reduce overload",
            params={"target": "non_critical_loads"},
        ),
        PlaybookStep(
            action_type="rebalance",
            description="Re-dispatch generation to restore safe power flow",
            params={},
        ),
    ],
    "scada_replay": [
        PlaybookStep(
            action_type="force_reread",
            description="Force fresh sensor reads bypassing cached SCADA values",
            params={},
        ),
        PlaybookStep(
            action_type="diff_check",
            description="Diff live readings against replayed values to confirm mismatch",
            params={"tolerance_pct": 5.0},
        ),
    ],
    "false_data_injection": [
        PlaybookStep(
            action_type="isolate_sensor",
            description="Mark sensor as untrusted and exclude from control loop",
            params={},
        ),
        PlaybookStep(
            action_type="cross_validate",
            description="Cross-validate with adjacent sensor nodes",
            params={},
        ),
    ],
    "actuator_hijack": [
        PlaybookStep(
            action_type="revoke_actuator_command",
            description="Send override command to return actuator to safe state",
            params={},
        ),
        PlaybookStep(
            action_type="verify_state",
            description="Confirm actuator state matches commanded position",
            params={},
        ),
    ],
}


def get_playbook(threat_class: str) -> Optional[List[PlaybookStep]]:
    """Return steps for the given threat class (case-insensitive), or None."""
    return PLAYBOOKS.get(threat_class.lower())


def execute_playbook(
    threat_class: str,
    node_id: str,
    twin,
    wn=None,
    net=None,
) -> Optional[Dict[str, Any]]:
    """
    Run the playbook for threat_class against node_id.
    Returns a summary dict, or None if no playbook exists.
    """
    steps = get_playbook(threat_class)
    if steps is None:
        return None

    executed = []
    for step in steps:
        _dispatch_step(step, node_id, twin, wn, net)
        executed.append(step.action_type)

    return {
        "threat_class": threat_class.lower(),
        "node_id": node_id,
        "steps_executed": len(executed),
        "actions": executed,
    }


def _dispatch_step(step: PlaybookStep, node_id: str, twin, wn, net) -> None:
    if step.action_type == "close_valve":
        if hasattr(twin, "close_valve"):
            twin.close_valve(node_id, wn)
    elif step.action_type == "shed_load":
        if hasattr(twin, "shed_load"):
            twin.shed_load(node_id, net)
    elif step.action_type == "rebalance":
        if hasattr(twin, "rebalance"):
            twin.rebalance(net)
    elif step.action_type == "force_reread":
        if hasattr(twin, "force_reread"):
            twin.force_reread(node_id)
    elif step.action_type == "revoke_actuator_command":
        if hasattr(twin, "revoke_actuator_command"):
            twin.revoke_actuator_command(node_id)
