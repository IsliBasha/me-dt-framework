"""
ME-DT Framework — Main entry point
Wires: Layer1 → Layer2 → Layer3 → Baselines → Layer4 (async) → Layer5 → WebSocket broadcast
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from layers.layer1_physical import init_water_network, init_power_network, run_tick
from layers.layer2_ingestion import process_batch
from layers.layer3_twin import DigitalTwin
from layers.layer4_mythos import (
    run_mode_a, run_mode_b, run_mode_c,
    get_recent_transcripts, reset_transcripts,
)
from layers.layer5_response import ResponseEngine
from layers.approval_queue import ApprovalQueue
from baselines import cusum_detector, isolation_forest
from attacks import scenario_library
from utils import terminal_monitor, metrics, logger

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="ME-DT Framework")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------------
# Global simulation state
# ---------------------------------------------------------------------------
_wn   = None
_net  = None
_orig_impedances = None
_orig_loads = None
_approval_queue = ApprovalQueue()
_twin   = DigitalTwin()
_engine = ResponseEngine(approval_queue=_approval_queue)

_tick:      int   = 0
_speed:     float = 1.0
_running:   bool  = True
_attack_state: Dict[str, Any] = {}

# Latest broadcast payload (for late-connecting clients)
_last_payload: Dict = {}

# Pending AI results from background tasks
_pending_mode_a: Optional[Any] = None
_pending_mode_b: Optional[Dict] = None
_pending_mode_c: Optional[List] = None

# Vulnerability atlas
_vulnerability_atlas: List[Dict] = []

# WebSocket connections
_connections: Set[WebSocket] = set()


# ---------------------------------------------------------------------------
# Mode C gate — pure function, testable without asyncio
# ---------------------------------------------------------------------------

def _should_fire_mode_c(
    mode_a_result: Optional[Any],
    violations: List,
    api_key: str,
) -> bool:
    """Return True only when real-AI uncertainty warrants zero-day hypothesis generation.

    Requires all three conditions:
      1. api_key is set — mock confidence (0.10) must not trigger Mode C in demo mode
      2. Mode A returned a result with confidence strictly below 0.40
      3. At least one active physics violation exists to explain
    """
    if not api_key:
        return False
    if mode_a_result is None:
        return False
    if mode_a_result.confidence >= 0.40:
        return False
    if not violations:
        return False
    return True


def _on_shutdown(tick: int):
    """Export the TTD comparison report on server stop. Called from main() finally block."""
    return metrics.export_report(tick)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        if _last_payload:
            await websocket.send_text(json.dumps(_last_payload, default=str))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)


async def _broadcast(payload: Dict):
    global _last_payload
    _last_payload = payload
    dead = set()
    data = json.dumps(payload, default=str)
    for ws in list(_connections):
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
@app.post("/api/inject-attack")
async def inject_attack(request: Request):
    body = await request.json()
    scenario = body.get("scenario", "")
    delay    = int(body.get("delay", 0))
    from models.attack_scenarios import SCENARIO_DEFINITIONS
    if scenario not in SCENARIO_DEFINITIONS:
        return JSONResponse({"error": "unknown scenario"}, status_code=400)
    scenario_library.inject(scenario, _tick, delay)
    metrics.record_injection(scenario, _tick + delay)
    logger.log_attack_injection(scenario, _tick + delay)
    return {"status": "scheduled", "scenario": scenario, "start_tick": _tick + delay}


@app.get("/api/state")
async def get_state():
    return _twin.get_state_snapshot()


@app.get("/api/metrics")
async def get_metrics():
    return metrics.get_summary()


@app.get("/api/report")
async def get_report():
    return metrics.export_report(_tick)


@app.post("/api/reset")
async def reset_sim():
    global _tick, _twin, _engine, _approval_queue, _vulnerability_atlas, _attack_state
    global _pending_mode_a, _pending_mode_b, _pending_mode_c
    _tick = 0
    _approval_queue = ApprovalQueue()
    _twin  = DigitalTwin()
    _engine = ResponseEngine(approval_queue=_approval_queue)
    _vulnerability_atlas = []
    _attack_state = {}
    _pending_mode_a = _pending_mode_b = _pending_mode_c = None
    scenario_library.reset_all()
    cusum_detector.reset_all()
    isolation_forest.reset()
    metrics.reset()
    reset_transcripts()
    return {"status": "reset"}


@app.get("/api/approval-queue")
async def get_approval_queue():
    return {
        "pending":  [a.to_dict() for a in _approval_queue.pending()],
        "approved": [a.to_dict() for a in _approval_queue.approved()],
        "all":      _approval_queue.all_as_dicts(),
    }


@app.post("/api/approve-action")
async def approve_action(request: Request):
    body = await request.json()
    action_id   = body.get("action_id", "")
    approved_by = body.get("approved_by", "operator")
    try:
        action = _approval_queue.approve(action_id, approved_by=approved_by)
        _twin.quarantine_node(action.node_id)
        logger.log_event("APPROVAL", {"action_id": action_id, "approved_by": approved_by, "node_id": action.node_id})
        return {"status": "approved", "action": action.to_dict()}
    except KeyError:
        return JSONResponse({"error": f"action '{action_id}' not found"}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)


@app.post("/api/reject-action")
async def reject_action(request: Request):
    body = await request.json()
    action_id   = body.get("action_id", "")
    rejected_by = body.get("rejected_by", "operator")
    reason      = body.get("reason")
    try:
        action = _approval_queue.reject(action_id, rejected_by=rejected_by, reason=reason)
        logger.log_event("REJECTION", {"action_id": action_id, "rejected_by": rejected_by, "reason": reason})
        return {"status": "rejected", "action": action.to_dict()}
    except KeyError:
        return JSONResponse({"error": f"action '{action_id}' not found"}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)


@app.get("/api/transcripts")
async def get_transcripts(n: int = 20):
    return get_recent_transcripts(min(n, 50))


@app.post("/api/speed")
async def set_speed(request: Request):
    global _speed
    body = await request.json()
    _speed = max(0.1, min(10.0, float(body.get("multiplier", 1.0))))
    return {"speed": _speed}


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------
async def simulation_loop():
    global _tick, _pending_mode_a, _pending_mode_b, _pending_mode_c, _vulnerability_atlas

    while _running:
        t_start = time.perf_counter()

        # --- Layer 1 — Physical simulation (run in thread pool, non-blocking) ---
        batch = await asyncio.get_event_loop().run_in_executor(
            None, _run_physical_tick
        )

        # Apply any scheduled attacks
        active_attacks = scenario_library.apply_attacks(_tick, _wn, _net, _attack_state)

        # Cross-domain cascade: force traffic signals in attack_state
        if _attack_state.get("traffic_all_green"):
            for nd in batch.get("traffic", {}).values():
                nd["signal_phase"] = "GREEN"

        # --- Layer 2 — Ingestion ---
        clean_stream, anomaly_sidecar = process_batch(batch, _attack_state)

        # --- Layer 3 — Twin update ---
        _twin.update(clean_stream, _tick)
        violations = _twin.active_violations

        # --- Baselines (sync, fast) ---
        cusum_alerts = cusum_detector.process_tick(clean_stream, _tick)
        isoforest_alert = isolation_forest.process_tick(clean_stream, _tick)

        # Record baseline detections
        for ca in cusum_alerts:
            metrics.record_detection("CUSUM", None, _tick)
            logger.log_alert("CUSUM", _tick, "MEDIUM", f"{ca.node_id} {ca.direction}")
        if isoforest_alert:
            metrics.record_detection("ISOFOREST", None, _tick)
            logger.log_alert("ISOFOREST", _tick, "MEDIUM", f"score={isoforest_alert.anomaly_score}")

        # --- Layer 4 — AI (async, non-blocking) ---
        # Collect any completed AI results from previous tick tasks
        mode_a_result = _pending_mode_a
        mode_b_result = _pending_mode_b
        mode_c_result = _pending_mode_c
        _pending_mode_a = _pending_mode_b = _pending_mode_c = None

        # Fire new AI tasks (results arrive in a future tick)
        state_snapshot = _twin.get_sandboxed_clone()
        violations_dict = [
            {
                "rule_id": v.rule_id, "description": v.description,
                "affected_nodes": v.affected_nodes, "subsystem": v.subsystem,
                "severity": v.severity, "tick": v.tick,
                "timestamp_iso": v.timestamp_iso, "cross_domain": v.cross_domain,
                "traffic_model": v.traffic_model,
            }
            for v in violations
        ]
        atlas_copy = list(_vulnerability_atlas)
        asyncio.create_task(_fire_mode_a(state_snapshot, violations_dict, anomaly_sidecar, atlas_copy))
        if _tick % config.PROBING_INTERVAL_TICKS == 0:
            asyncio.create_task(_fire_mode_b(state_snapshot))
        # Mode C: genuine AI uncertainty + real key (mock confidence must not trigger)
        if _should_fire_mode_c(mode_a_result, violations, config.ANTHROPIC_API_KEY):
            asyncio.create_task(_fire_mode_c(state_snapshot, violations_dict, anomaly_sidecar))

        # --- Layer 5 — Response ---
        response = _engine.process(
            _tick,
            mode_a_result, mode_b_result, mode_c_result,
            cusum_alerts, isoforest_alert,
            violations_dict, _twin, _wn, _net,
        )

        # Record ME-DT detections
        if mode_a_result and mode_a_result.confidence >= config.ALERT_THRESHOLD:
            metrics.record_detection("ME-DT", mode_a_result.threat_class, _tick)
            metrics.record_latency(mode_a_result.api_latency_ms)
            metrics.record_class_alert(mode_a_result.threat_class)
            logger.log_alert("ME-DT", _tick, response["threat_level"], mode_a_result.evidence_trace)

        # Update atlas from Mode B
        if mode_b_result:
            _vulnerability_atlas.append(mode_b_result)
            _vulnerability_atlas = _vulnerability_atlas[-20:]

        # --- Build broadcast payload ---
        twin_state = _twin.get_state_snapshot()
        active_attack_name = next(
            (name for name, active in active_attacks.items() if active), None
        )
        metrics_summary = metrics.get_summary()

        payload = {
            "tick":          _tick,
            "threat_level":  response["threat_level"],
            "twin_state": {
                "water":   {k: v for k, v in twin_state["water"].items()},
                "power":   {k: v for k, v in twin_state["power"].items()},
                "traffic": {k: v for k, v in twin_state["traffic"].items()},
            },
            "violations":       violations_dict,
            "mode_a": _ta_to_dict(mode_a_result),
            "mode_b": mode_b_result,
            "mode_c": response.get("mode_c"),
            "cusum_alerts":     [
                {"node_id": ca.node_id, "direction": ca.direction,
                 "tick": ca.tick, "accumulator_value": ca.accumulator_value}
                for ca in cusum_alerts
            ],
            "isoforest_alert": {
                "tick": isoforest_alert.tick,
                "anomaly_score": isoforest_alert.anomaly_score,
            } if isoforest_alert else None,
            "metrics":           metrics_summary,
            "vulnerability_atlas": _vulnerability_atlas[-10:],
            "event_log":         _engine.get_recent_events(50),
            "active_attack":     active_attack_name,
        }

        await _broadcast(payload)

        terminal_monitor.print_tick_summary(
            _tick, response["threat_level"], violations_dict,
            mode_a_result, len(cusum_alerts), isoforest_alert is not None,
            active_attack_name, _speed,
        )

        _tick += 1

        # Respect tick interval
        elapsed  = time.perf_counter() - t_start
        interval = config.TICK_INTERVAL_S / _speed
        sleep_t  = max(0.0, interval - elapsed)
        if sleep_t > 0:
            await asyncio.sleep(sleep_t)


def _run_physical_tick() -> Dict:
    """Synchronous: run physical simulators, return batch."""
    return run_tick(_tick, _wn, _net, _attack_state)


async def _fire_mode_a(state, violations, anomaly_sidecar, atlas):
    global _pending_mode_a
    result = await run_mode_a(state, violations, anomaly_sidecar, atlas, _tick)
    _pending_mode_a = result


async def _fire_mode_b(state):
    global _pending_mode_b
    result = await run_mode_b(state, _tick)
    _pending_mode_b = result


async def _fire_mode_c(state, violations, anomaly_sidecar):
    global _pending_mode_c
    result = await run_mode_c(state, violations, anomaly_sidecar, _tick)
    _pending_mode_c = result


def _ta_to_dict(ta) -> Optional[Dict]:
    if ta is None:
        return None
    return {
        "threat_class":          ta.threat_class,
        "confidence":            ta.confidence,
        "evidence_trace":        ta.evidence_trace,
        "affected_subsystems":   ta.affected_subsystems,
        "physical_consequence":  ta.physical_consequence,
        "recommended_response":  ta.recommended_response,
        "reasoning_chain":       ta.reasoning_chain,
        "tick":                  ta.tick,
        "api_latency_ms":        ta.api_latency_ms,
    }


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------
async def start_uvicorn():
    cfg = uvicorn.Config(
        app,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(cfg)
    await server.serve()


async def main():
    global _wn, _net, _orig_impedances, _orig_loads
    print("=== ME-DT Framework starting ===")
    print(f"  Water: WNTR/Net3     | Power: pandapower/case33bw")
    print(f"  Traffic: SYNTHETIC   | AI: {'ENABLED' if config.ANTHROPIC_API_KEY else 'DEMO MODE (no API key)'}")
    print(f"  Server: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print("================================\n")

    # Init simulators
    _wn = init_water_network()
    _net, _orig_impedances, _orig_loads = init_power_network()

    os.makedirs("reports", exist_ok=True)

    try:
        await asyncio.gather(
            simulation_loop(),
            start_uvicorn(),
        )
    finally:
        _on_shutdown(_tick)


if __name__ == "__main__":
    asyncio.run(main())
