"""
Layer 2 — Data Ingestion
Normalizes raw telemetry, validates integrity, computes rolling stats,
produces clean stream (→ Layer 3) and anomaly sidecar (→ Layer 4).
"""

import hashlib
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

from models.state_vector import NodeReading, AnomalyEvent

ROLLING_WINDOW = 20

_PROTOCOL_MAP = {
    "water":   "Modbus/TCP",
    "power":   "DNP3",
    "traffic": "MQTT",
}

# node_id -> deque of recent values
_rolling_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=ROLLING_WINDOW))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verify_hash(node_id: str, value: float, ts_ms: int, stored_hash: str) -> bool:
    expected = hashlib.sha256(f"{node_id}{value}{ts_ms}".encode()).hexdigest()[:16]
    return expected == stored_hash


def _get_rolling_stats(node_id: str) -> Tuple[Optional[float], Optional[float]]:
    hist = _rolling_history[node_id]
    if len(hist) < 3:
        return None, None
    vals = list(hist)
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = variance ** 0.5
    return mean, std


def _primary_value(raw: Dict) -> Optional[float]:
    """Extract the main numeric signal from a raw node dict."""
    for key in ("pressure", "vm_pu", "vehicle_flow", "value"):
        if key in raw and isinstance(raw[key], (int, float)):
            return float(raw[key])
    return None


def _normalize_node(
    node_id: str,
    subsystem: str,
    raw: Dict,
    tick: int,
) -> NodeReading:
    ts_iso = raw.get("timestamp_iso", _iso_now())
    ts_ms  = raw.get("timestamp_ms", 0)
    proto  = _PROTOCOL_MAP.get(subsystem, "UNKNOWN")

    primary = _primary_value(raw)
    value   = primary if primary is not None else 0.0
    unit    = raw.get("unit", "")

    metric = "pressure" if subsystem == "water" else (
        "vm_pu" if subsystem == "power" else "vehicle_flow"
    )

    source = raw.get("source", "SIMULATED")

    return NodeReading(
        node_id=node_id,
        subsystem=subsystem,
        metric=metric,
        value=value,
        unit=unit,
        protocol=proto,
        timestamp_iso=ts_iso,
        timestamp_ms=ts_ms,
        confidence=1.0,
        source=source,
        integrity_hash=raw.get("integrity_hash", ""),
        status=raw.get("status", "NORMAL"),
    )


def process_batch(
    batch: Dict,
    active_attacks: Dict,
) -> Tuple[List[NodeReading], List[AnomalyEvent]]:
    """
    Returns:
      clean_stream  — normalized NodeReading list → Layer 3
      anomaly_sidecar — AnomalyEvent list → Layer 4 priority queue
    """
    tick       = batch.get("tick", 0)
    clean:    List[NodeReading]   = []
    anomalies: List[AnomalyEvent] = []

    # DoS simulation — drop water packets with 80% probability
    dos_active = active_attacks.get("denial_of_service_ot", {}).get("active", False)

    for subsystem in ("water", "power", "traffic"):
        nodes = batch.get(subsystem, {})
        for node_id, raw in nodes.items():
            if node_id.startswith("__"):
                continue
            # Pump status nodes — pass through so Layer 3 W3 can track toggles
            if raw.get("pump"):
                reading = _normalize_node(node_id, subsystem, raw, tick)
                clean.append(reading)
                continue

            # DoS drop simulation
            if dos_active and subsystem == "water":
                import random
                if random.random() < 0.80:
                    anomalies.append(AnomalyEvent(
                        node_id=node_id,
                        subsystem=subsystem,
                        event_type="MISSING",
                        value=None,
                        rolling_mean=None,
                        rolling_std=None,
                        tick=tick,
                        timestamp_iso=_iso_now(),
                    ))
                    continue

            reading = _normalize_node(node_id, subsystem, raw, tick)

            # Integrity check
            if reading.integrity_hash:
                valid = _verify_hash(
                    node_id, reading.value, reading.timestamp_ms, reading.integrity_hash
                )
                if not valid:
                    reading.confidence = 0.0

            # Rolling stats + anomaly flag
            primary = _primary_value(raw)
            if primary is not None:
                _rolling_history[node_id].append(primary)
                mean, std = _get_rolling_stats(node_id)
                if mean is not None and std is not None and std > 0:
                    if abs(primary - mean) > 3 * std:
                        reading.status = "SUSPECT"
                        anomalies.append(AnomalyEvent(
                            node_id=node_id,
                            subsystem=subsystem,
                            event_type="SUSPECT",
                            value=primary,
                            rolling_mean=mean,
                            rolling_std=std,
                            tick=tick,
                            timestamp_iso=_iso_now(),
                        ))

            clean.append(reading)

    return clean, anomalies
