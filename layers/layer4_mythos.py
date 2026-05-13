"""
Layer 4 — Mythos AI Engine
Three asyncio coroutines: Mode A (continuous), Mode B (adversarial),
Mode C (zero-day hypothesis). Never blocks the tick loop.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from models.state_vector import (
    ThreatAssessment, AttackPath, AttackStep, ZeroDayHypothesis
)
from models.threat_model import THREAT_TAXONOMY

try:
    import anthropic
    _client: Optional[anthropic.AsyncAnthropic] = None
    _ANTHROPIC_OK = True
except ImportError:
    _ANTHROPIC_OK = False
    _client = None
    print("[Layer4] WARNING: anthropic SDK not installed")


def get_client() -> Optional["anthropic.AsyncAnthropic"]:
    global _client
    if not _ANTHROPIC_OK:
        return None
    if _client is None and config.ANTHROPIC_API_KEY:
        _client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Prompt context builder
# ---------------------------------------------------------------------------

def build_context(
    state_snapshot: Dict,
    violations: List[Dict],
    anomaly_sidecar: List,
    vulnerability_atlas: List,
) -> str:
    tick = state_snapshot.get("tick", 0)
    ts   = datetime.now(timezone.utc).isoformat()

    # Top 5 water nodes by deviation
    water = state_snapshot.get("water", {})
    water_lines = []
    for nid, nd in list(water.items())[:5]:
        val = nd.get("value") or nd.get("pressure") or 0
        water_lines.append(f"  {nid}: {val:.2f} {nd.get('unit','m')}")

    # Power buses with issues
    power = state_snapshot.get("power", {})
    power_lines = []
    for nid, nd in power.items():
        vm = nd.get("vm_pu") or nd.get("value") or 1.0
        lp = nd.get("loading_pct") or nd.get("loading_percent") or 0
        if isinstance(vm, float) and (vm < 0.95 or lp > 80):
            power_lines.append(f"  bus {nid}: vm_pu={vm:.3f} loading={lp:.1f}%")

    # Traffic anomalies (clearly synthetic)
    traffic = state_snapshot.get("traffic", {})
    traffic_lines = []
    for nid, nd in list(traffic.items())[:3]:
        flow = nd.get("vehicle_flow") or nd.get("value") or 0
        phase = nd.get("signal_phase", "?")
        traffic_lines.append(f"  {nid} [SYNTHETIC]: flow={flow:.1f} veh/min phase={phase}")

    # Violations summary
    viol_lines = [
        f"  [{v.get('severity','?')}] {v.get('rule_id','?')}: {v.get('description','?')} "
        f"nodes={v.get('affected_nodes',[][:3])}"
        for v in violations[:6]
    ]

    # Anomaly sidecar
    anomaly_lines = [
        f"  {a.node_id} ({a.subsystem}): {a.event_type} "
        f"value={a.value} mean={a.rolling_mean:.2f if a.rolling_mean else 'N/A'}"
        for a in anomaly_sidecar[:5]
    ]

    # Vulnerability atlas
    atlas_summary = f"{len(vulnerability_atlas)} paths found"
    if vulnerability_atlas:
        top = vulnerability_atlas[-1]
        atlas_summary += f", latest entry_point={top.get('entry_point','')} difficulty={top.get('detection_difficulty','')}"

    ctx = f"""TICK: {tick}  TIMESTAMP: {ts}

ACTIVE PHYSICS VIOLATIONS ({len(violations)}):
{chr(10).join(viol_lines) if viol_lines else "  None"}

ANOMALY SIDECAR EVENTS ({len(anomaly_sidecar)}):
{chr(10).join(anomaly_lines) if anomaly_lines else "  None"}

WATER STATE (Net3 WNTR simulation — top 5 nodes):
{chr(10).join(water_lines) if water_lines else "  No data"}

POWER STATE (IEEE case33bw pandapower — buses with issues):
{chr(10).join(power_lines) if power_lines else "  All buses nominal"}

TRAFFIC STATE (SYNTHETIC DATA — illustrative only):
{chr(10).join(traffic_lines) if traffic_lines else "  No data"}

VULNERABILITY ATLAS: {atlas_summary}

THREAT TAXONOMY: {" | ".join(THREAT_TAXONOMY)}
"""
    return ctx


# ---------------------------------------------------------------------------
# Mode A — Continuous Analysis
# ---------------------------------------------------------------------------

_MODE_A_SYSTEM = """You are the Mythos AI threat detection engine embedded
in a smart city digital twin framework. You analyze real-time
cyber-physical state data from two physically simulated subsystems
(water network modeled with WNTR/Net3, power grid modeled with
pandapower/IEEE case33bw) and one synthetic traffic subsystem.

Your role: detect cyber-physical attacks by reasoning about patterns
across subsystems, not just individual sensor thresholds. Consider
attacker intent, physical plausibility, and cross-domain correlations.

Respond ONLY in valid JSON matching this exact schema:
{
  "threat_class": "<taxonomy class or NONE>",
  "confidence": <float 0.0-1.0>,
  "evidence_trace": "<one sentence explaining the key evidence>",
  "affected_subsystems": ["water"|"power"|"traffic"],
  "physical_consequence": "<predicted real-world effect if unaddressed>",
  "recommended_response": "<specific actionable response>",
  "reasoning_chain": "<2-3 sentences of chain-of-thought reasoning>"
}"""


async def run_mode_a(
    state_snapshot: Dict,
    violations: List[Dict],
    anomaly_sidecar: List,
    vulnerability_atlas: List,
    tick: int,
) -> Optional[ThreatAssessment]:
    client = get_client()
    if client is None:
        return _mock_mode_a(tick)

    ctx = build_context(state_snapshot, violations, anomaly_sidecar, vulnerability_atlas)
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_A,
                system=_MODE_A_SYSTEM,
                messages=[{"role": "user", "content": ctx + "\nAnalyze the current state."}],
            ),
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        raw = resp.content[0].text.strip()
        data = json.loads(raw)
        return ThreatAssessment(
            threat_class=data.get("threat_class", "UNKNOWN"),
            confidence=float(data.get("confidence", 0.0)),
            evidence_trace=data.get("evidence_trace", ""),
            affected_subsystems=data.get("affected_subsystems", []),
            physical_consequence=data.get("physical_consequence", ""),
            recommended_response=data.get("recommended_response", ""),
            reasoning_chain=data.get("reasoning_chain", ""),
            tick=tick,
            api_latency_ms=round(latency_ms, 1),
        )
    except json.JSONDecodeError as e:
        print(f"[Layer4/A] JSON decode error at tick {tick}: {e}")
        return None
    except asyncio.TimeoutError:
        print(f"[Layer4/A] Timeout at tick {tick}")
        return None
    except Exception as e:
        print(f"[Layer4/A] API error at tick {tick}: {e}")
        return None


# ---------------------------------------------------------------------------
# Mode B — Adversarial Probing
# ---------------------------------------------------------------------------

_MODE_B_SYSTEM = """You are a red-team AI adversary with full knowledge of
a smart city's cyber-physical infrastructure. You have read access to
the digital twin state. Your goal: identify the most exploitable attack
path that would cause physical harm while evading statistical detectors
(CUSUM threshold h=5 and Isolation Forest).

Respond ONLY in valid JSON:
{
  "entry_point": "<specific node_id and subsystem>",
  "attack_steps": [
    {"step": 1, "action": "...", "target_node": "...", "expected_effect": "..."},
    {"step": 2, "action": "...", "target_node": "...", "expected_effect": "..."}
  ],
  "physical_consequence": "<real-world physical harm>",
  "detection_difficulty": "LOW|MEDIUM|HIGH",
  "evasion_rationale": "<why CUSUM and IsolationForest would miss this>",
  "estimated_impact_severity": <int 1-10>
}"""


async def run_mode_b(
    state_snapshot: Dict,
    tick: int,
) -> Optional[Dict]:
    client = get_client()
    if client is None:
        return _mock_mode_b(tick)

    clone = json.dumps(state_snapshot, default=str)[:4000]
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_B,
                system=_MODE_B_SYSTEM,
                messages=[{"role": "user", "content": f"Red-team target:\n{clone}"}],
            ),
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        raw = resp.content[0].text.strip()
        data = json.loads(raw)
        data["tick"] = tick
        return data
    except Exception as e:
        print(f"[Layer4/B] Error at tick {tick}: {e}")
        return None


# ---------------------------------------------------------------------------
# Mode C — Zero-Day Hypothesis
# ---------------------------------------------------------------------------

_MODE_C_SYSTEM = """You are a cybersecurity research AI analyzing an anomaly
in a smart city digital twin that does not match any known attack
signature. The infrastructure uses real hydraulic simulation (WNTR/Net3)
and real power flow simulation (pandapower/case33bw).

Generate 3 ranked attack hypotheses that could explain this anomaly.
Respond ONLY in valid JSON:
{
  "hypotheses": [
    {
      "rank": 1,
      "attack_class": "...",
      "attacker_intent": "...",
      "physical_impact_severity": <int 1-10>,
      "why_standard_ids_misses": "...",
      "recommended_monitoring": "..."
    },
    {
      "rank": 2,
      "attack_class": "...",
      "attacker_intent": "...",
      "physical_impact_severity": <int 1-10>,
      "why_standard_ids_misses": "...",
      "recommended_monitoring": "..."
    },
    {
      "rank": 3,
      "attack_class": "...",
      "attacker_intent": "...",
      "physical_impact_severity": <int 1-10>,
      "why_standard_ids_misses": "...",
      "recommended_monitoring": "..."
    }
  ]
}"""


async def run_mode_c(
    state_snapshot: Dict,
    violations: List[Dict],
    anomaly_sidecar: List,
    tick: int,
) -> Optional[List[ZeroDayHypothesis]]:
    client = get_client()
    if client is None:
        return _mock_mode_c(tick)

    anomaly_details = {
        "tick": tick,
        "violations": violations,
        "anomaly_events": [
            {"node_id": a.node_id, "type": a.event_type, "value": a.value}
            for a in anomaly_sidecar[:10]
        ],
    }
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_C,
                system=_MODE_C_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": f"Unexplained anomaly:\n{json.dumps(anomaly_details, default=str)}",
                }],
            ),
            timeout=30.0,
        )
        raw = resp.content[0].text.strip()
        data = json.loads(raw)
        results = []
        for h in data.get("hypotheses", []):
            results.append(ZeroDayHypothesis(
                rank=h.get("rank", 0),
                attack_class=h.get("attack_class", "UNKNOWN"),
                attacker_intent=h.get("attacker_intent", ""),
                physical_impact_severity=h.get("physical_impact_severity", 5),
                why_standard_ids_misses=h.get("why_standard_ids_misses", ""),
                recommended_monitoring=h.get("recommended_monitoring", ""),
            ))
        return results
    except Exception as e:
        print(f"[Layer4/C] Error at tick {tick}: {e}")
        return None


# ---------------------------------------------------------------------------
# Mock responses (used when API key not set)
# ---------------------------------------------------------------------------

def _mock_mode_a(tick: int) -> ThreatAssessment:
    return ThreatAssessment(
        threat_class="NONE",
        confidence=0.1,
        evidence_trace="[DEMO MODE — no API key] System nominal.",
        affected_subsystems=[],
        physical_consequence="None detected.",
        recommended_response="Set ANTHROPIC_API_KEY to enable live AI analysis.",
        reasoning_chain="Running in demo mode without Anthropic API key.",
        tick=tick,
        api_latency_ms=0.0,
    )


def _mock_mode_b(tick: int) -> Dict:
    return {
        "entry_point": "bus_32/power",
        "attack_steps": [
            {"step": 1, "action": "Disable feeder line", "target_node": "line_31", "expected_effect": "Load redistribution"},
            {"step": 2, "action": "Exploit resulting overload", "target_node": "bus_32", "expected_effect": "Voltage collapse"},
        ],
        "physical_consequence": "[DEMO MODE] Would cause end-of-feeder voltage collapse.",
        "detection_difficulty": "HIGH",
        "evasion_rationale": "[DEMO] Sub-threshold incremental changes evade both CUSUM and IsoForest.",
        "estimated_impact_severity": 7,
        "tick": tick,
    }


def _mock_mode_c(tick: int) -> List[ZeroDayHypothesis]:
    return [
        ZeroDayHypothesis(
            rank=1,
            attack_class="SUPPLY_CHAIN_COMPROMISE",
            attacker_intent="[DEMO MODE] Firmware manipulation of field devices.",
            physical_impact_severity=9,
            why_standard_ids_misses="Appears as normal sensor drift.",
            recommended_monitoring="Cross-reference physical inspection logs with sensor deviations.",
        )
    ]
