"""
Layer 4 — Mythos AI Engine
Three asyncio coroutines: Mode A (continuous), Mode B (adversarial),
Mode C (zero-day hypothesis). Never blocks the tick loop.
"""

import asyncio
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import config
import utils.audit_log as audit_log
from models.state_vector import (
    ThreatAssessment, AttackPath, AttackStep, ZeroDayHypothesis
)
from models.threat_model import THREAT_TAXONOMY, KNOWN_THREATS

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
# Transcript log — bounded in-memory ring buffer + JSONL audit file
# ---------------------------------------------------------------------------

_transcript_counter: int = 0
_transcript_log: "deque[Dict]" = deque(maxlen=50)


def _append_transcript(
    mode: str,
    tick: int,
    prompt: str,
    response_raw: str,
    parsed_result: Any,
    latency_ms: float,
) -> None:
    global _transcript_counter
    _transcript_counter += 1
    entry: Dict[str, Any] = {
        "id": _transcript_counter,
        "tick": tick,
        "mode": mode,
        "prompt": prompt,
        "response_raw": response_raw,
        "parsed_result": parsed_result,
        "latency_ms": round(latency_ms, 1),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
    }
    _transcript_log.append(entry)
    audit_log.append_transcript(entry)


def get_recent_transcripts(n: int = 20) -> List[Dict]:
    entries = list(_transcript_log)
    return entries[-n:] if len(entries) > n else entries


def reset_transcripts() -> None:
    global _transcript_counter
    _transcript_counter = 0
    _transcript_log.clear()


# ---------------------------------------------------------------------------
# Mode A Response Cache (Ticket 5)
# key = hash(violations + anomaly summary + top water values)
# value = (ThreatAssessment, stored_tick)
# ---------------------------------------------------------------------------

_mode_a_cache: Dict[str, Tuple[Any, int]] = {}
_cache_hits:   int = 0
_cache_misses: int = 0


def _cache_key(violations: List[Dict], anomaly_sidecar: List, state_snapshot: Dict) -> str:
    water = state_snapshot.get("water", {})
    water_vals = sorted(
        [(nid, float(nd.get("value") or nd.get("pressure") or 0))
         for nid, nd in water.items()
         if nd],
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:8]
    payload = json.dumps(
        {
            "violations": [{"rule_id": v.get("rule_id"), "severity": v.get("severity")} for v in violations],
            "water": water_vals,
            "anomaly_count": len(anomaly_sidecar),
            "anomaly_nodes": [getattr(a, "node_id", "") for a in anomaly_sidecar[:5]],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_cache_stats() -> Dict[str, Any]:
    total = _cache_hits + _cache_misses
    return {
        "hits":     _cache_hits,
        "misses":   _cache_misses,
        "hit_rate": round(_cache_hits / total, 4) if total else 0.0,
    }


def reset_cache() -> None:
    global _cache_hits, _cache_misses
    _mode_a_cache.clear()
    _cache_hits   = 0
    _cache_misses = 0


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

    # Water: show all nodes sorted by absolute pressure value (highest first — most affected)
    water = state_snapshot.get("water", {})
    water_entries = []
    for nid, nd in water.items():
        val = nd.get("value") or nd.get("pressure") or 0
        try:
            water_entries.append((nid, float(val), nd.get("unit", "m")))
        except (TypeError, ValueError):
            pass
    water_entries.sort(key=lambda x: abs(x[1]), reverse=True)
    water_lines = [f"  {nid}: {val:.2f} {unit}" for nid, val, unit in water_entries[:10]]

    # Power: all buses, flag anomalous ones
    power = state_snapshot.get("power", {})
    power_lines = []
    for nid, nd in power.items():
        vm = nd.get("vm_pu") or nd.get("value") or 1.0
        lp = nd.get("loading_pct") or nd.get("loading_percent") or 0
        try:
            vm, lp = float(vm), float(lp)
        except (TypeError, ValueError):
            continue
        flag = " *** ANOMALOUS ***" if (vm < 0.95 or lp > 80) else ""
        power_lines.append(f"  bus {nid}: vm_pu={vm:.3f} loading={lp:.1f}%{flag}")

    # Traffic (synthetic)
    traffic = state_snapshot.get("traffic", {})
    traffic_lines = []
    for nid, nd in list(traffic.items())[:3]:
        flow = nd.get("vehicle_flow") or nd.get("value") or 0
        phase = nd.get("signal_phase", "?")
        traffic_lines.append(f"  {nid} [SYNTHETIC]: flow={float(flow):.1f} veh/min phase={phase}")

    # Violations (all of them)
    viol_lines = [
        f"  [{v.get('severity','?')}] {v.get('rule_id','?')}: {v.get('description','?')} "
        f"nodes={v.get('affected_nodes',[])[:4]}"
        for v in violations
    ]

    # Anomaly sidecar — full list with event type counts
    missing_count = sum(1 for a in anomaly_sidecar if getattr(a, "event_type", "") == "MISSING")
    spike_count   = sum(1 for a in anomaly_sidecar if getattr(a, "event_type", "") in ("SPIKE", "HIGH", "LOW"))
    anomaly_lines = []
    for a in anomaly_sidecar[:15]:
        mean_str = f"{a.rolling_mean:.2f}" if getattr(a, "rolling_mean", None) is not None else "N/A"
        anomaly_lines.append(
            f"  {a.node_id} ({a.subsystem}): {a.event_type} value={a.value} mean={mean_str}"
        )

    # Signal fingerprint — pre-computed distinguishing features
    fingerprint_lines = [
        f"  MISSING events in sidecar: {missing_count}  (high count = DOS/OT indicator)",
        f"  SPIKE/anomaly events: {spike_count}",
        f"  Physics violations firing: {[v.get('rule_id') for v in violations]}",
        f"  Subsystems with violations: {list({v.get('subsystem') for v in violations})}",
        f"  Power buses below 0.95 pu: {sum(1 for nd in power.values() if float(nd.get('vm_pu') or nd.get('value') or 1.0) < 0.95)}",
        f"  Power buses overloaded >80%: {sum(1 for nd in power.values() if float(nd.get('loading_pct') or nd.get('loading_percent') or 0) > 80)}",
    ]

    # Vulnerability atlas
    atlas_summary = f"{len(vulnerability_atlas)} paths found"
    if vulnerability_atlas:
        top = vulnerability_atlas[-1]
        atlas_summary += f", latest entry_point={top.get('entry_point','')} difficulty={top.get('detection_difficulty','')}"

    ctx = f"""TICK: {tick}  TIMESTAMP: {ts}

SIGNAL FINGERPRINT (key distinguishing features — use this to select threat class):
{chr(10).join(fingerprint_lines)}

ACTIVE PHYSICS VIOLATIONS ({len(violations)}):
{chr(10).join(viol_lines) if viol_lines else "  None"}

ANOMALY SIDECAR ({len(anomaly_sidecar)} total events — showing up to 15):
{chr(10).join(anomaly_lines) if anomaly_lines else "  None"}

WATER STATE (Net3 WNTR — sorted by pressure magnitude, top 10):
{chr(10).join(water_lines) if water_lines else "  No data"}

POWER STATE (IEEE case33bw pandapower — all buses):
{chr(10).join(power_lines) if power_lines else "  All buses nominal"}

TRAFFIC STATE (SYNTHETIC DATA — illustrative only):
{chr(10).join(traffic_lines) if traffic_lines else "  No data"}

VULNERABILITY ATLAS: {atlas_summary}
"""
    return ctx


# ---------------------------------------------------------------------------
# Mode A — Continuous Analysis
# ---------------------------------------------------------------------------

_MODE_A_SYSTEM = """You are the Mythos AI threat detector for a smart city digital twin (WNTR water, pandapower power, synthetic traffic).

Classify the current state using ONLY these threat classes and their distinguishing signals:
- WATER_HAMMER: W1 rule firing, rapid pressure oscillation in water nodes
- FALSE_DATA_INJECTION: zero-demand with rising pressure (water W2/W3), or load mismatch (power P3/P4)
- LOAD_REDISTRIBUTION: P1/P2 rules, multiple power buses ANOMALOUS, loading >80%
- DENIAL_OF_SERVICE_OT: high MISSING event count in sidecar, few/no physics violations
- CROSS_DOMAIN_CASCADE: violations in BOTH water AND power simultaneously, X1/X2 rules
- SCADA_REPLAY: power P3 violation, stale topology readings
- ACTUATOR_HIJACK: chemical concentration spike in water nodes, actuator override
- RECONNAISSANCE: sub-threshold perturbations across many nodes, no violations firing
- NONE: truly nominal state

Use the SIGNAL FINGERPRINT section to classify. Do NOT default to DENIAL_OF_SERVICE_OT unless MISSING event count dominates and physics violations are absent.

Respond ONLY with valid JSON — no markdown, no code fences, no explanation outside the JSON:
{"threat_class":"...","confidence":0.0,"evidence_trace":"...","affected_subsystems":[],"physical_consequence":"...","recommended_response":"...","reasoning_chain":"..."}"""


async def run_mode_a(
    state_snapshot: Dict,
    violations: List[Dict],
    anomaly_sidecar: List,
    vulnerability_atlas: List,
    tick: int,
) -> Optional[ThreatAssessment]:
    global _cache_hits, _cache_misses

    # Cache lookup (mock path also benefits — same determinism)
    if config.MODE_A_CACHE_ENABLED:
        key = _cache_key(violations, anomaly_sidecar, state_snapshot)
        cached = _mode_a_cache.get(key)
        if cached is not None:
            result, stored_tick = cached
            if (tick - stored_tick) < config.MODE_A_CACHE_TTL_TICKS:
                _cache_hits += 1
                return result
            else:
                del _mode_a_cache[key]
        _cache_misses += 1

    client = get_client()
    ctx = build_context(state_snapshot, violations, anomaly_sidecar, vulnerability_atlas)
    prompt = ctx + "\nAnalyze the current state."
    t0 = time.perf_counter()

    if client is None:
        result = _mock_mode_a(tick)
        latency_ms = (time.perf_counter() - t0) * 1000
        _append_transcript("A", tick, prompt, "[DEMO MODE — no API key]",
                           _ta_to_dict(result), latency_ms)
        if config.MODE_A_CACHE_ENABLED:
            key = _cache_key(violations, anomaly_sidecar, state_snapshot)
            _mode_a_cache[key] = (result, tick)
        return result

    raw = ""
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_A,
                system=_MODE_A_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if Claude wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        result = ThreatAssessment(
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
        _append_transcript("A", tick, prompt, raw, _ta_to_dict(result), latency_ms)
        if config.MODE_A_CACHE_ENABLED:
            key = _cache_key(violations, anomaly_sidecar, state_snapshot)
            _mode_a_cache[key] = (result, tick)
        return result
    except json.JSONDecodeError as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"[Layer4/A] JSON decode error at tick {tick}: {e} | raw={raw[:120]!r}")
        _append_transcript("A", tick, prompt, raw, None, latency_ms)
        return None
    except asyncio.TimeoutError:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"[Layer4/A] Timeout at tick {tick}")
        _append_transcript("A", tick, prompt, "[TIMEOUT]", None, latency_ms)
        return None
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"[Layer4/A] API error at tick {tick}: {e}")
        _append_transcript("A", tick, prompt, f"[ERROR: {e}]", None, latency_ms)
        return None


def _ta_to_dict(ta: ThreatAssessment) -> Dict:
    return {
        "threat_class": ta.threat_class,
        "confidence": ta.confidence,
        "evidence_trace": ta.evidence_trace,
        "affected_subsystems": ta.affected_subsystems,
        "physical_consequence": ta.physical_consequence,
        "recommended_response": ta.recommended_response,
        "reasoning_chain": ta.reasoning_chain,
    }


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
    clone = json.dumps(state_snapshot, default=str)[:4000]
    prompt = f"Red-team target:\n{clone}"
    t0 = time.perf_counter()

    if client is None:
        result = _mock_mode_b(tick)
        latency_ms = (time.perf_counter() - t0) * 1000
        _append_transcript("B", tick, prompt, "[DEMO MODE — no API key]", result, latency_ms)
        return result

    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_B,
                system=_MODE_B_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        data["tick"] = tick
        _append_transcript("B", tick, prompt, raw, data, latency_ms)
        return data
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"[Layer4/B] Error at tick {tick}: {e}")
        _append_transcript("B", tick, prompt, f"[ERROR: {e}]", None, latency_ms)
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
    anomaly_details = {
        "tick": tick,
        "violations": violations,
        "anomaly_events": [
            {"node_id": a.node_id, "type": a.event_type, "value": a.value}
            for a in anomaly_sidecar[:10]
        ],
    }
    prompt = f"Unexplained anomaly:\n{json.dumps(anomaly_details, default=str)}"
    t0 = time.perf_counter()

    if client is None:
        result = _mock_mode_c(tick)
        latency_ms = (time.perf_counter() - t0) * 1000
        parsed = [{"rank": h.rank, "attack_class": h.attack_class,
                   "attacker_intent": h.attacker_intent} for h in result]
        _append_transcript("C", tick, prompt, "[DEMO MODE — no API key]", parsed, latency_ms)
        return result

    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.MAX_TOKENS_MODE_C,
                system=_MODE_C_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": prompt,
                }],
            ),
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
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
        parsed = [{"rank": h.rank, "attack_class": h.attack_class,
                   "attacker_intent": h.attacker_intent} for h in results]
        _append_transcript("C", tick, prompt, raw, parsed, latency_ms)
        return results
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"[Layer4/C] Error at tick {tick}: {e}")
        _append_transcript("C", tick, prompt, f"[ERROR: {e}]", None, latency_ms)
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
