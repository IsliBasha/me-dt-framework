"""Structured JSONL event logger."""

import json
import os
from datetime import datetime, timezone

_LOG_FILE = "reports/events.jsonl"


def _ensure_dir():
    os.makedirs("reports", exist_ok=True)


def log_event(event_type: str, data: dict):
    _ensure_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type":      event_type,
        **data,
    }
    with open(_LOG_FILE, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def log_attack_injection(scenario: str, tick: int):
    log_event("ATTACK_INJECTION", {"scenario": scenario, "tick": tick})


def log_alert(source: str, tick: int, severity: str, message: str):
    log_event("ALERT", {"source": source, "tick": tick, "severity": severity, "message": message})


def log_api_call(mode: str, tick: int, latency_ms: float, success: bool):
    log_event("API_CALL", {"mode": mode, "tick": tick, "latency_ms": latency_ms, "success": success})
