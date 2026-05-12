"""
CUSUM Detector — Page's cumulative sum algorithm (Page, 1954).
Parameters: k=0.5 (allowance), h=5.0 (threshold).
"""

from typing import Dict, List, Optional
from models.state_vector import CUSUMAlert
import config

# Per-node accumulator state
_S_high:  Dict[str, float] = {}
_S_low:   Dict[str, float] = {}
_mu:      Dict[str, float] = {}
_sigma:   Dict[str, float] = {}
_warmup:  Dict[str, List[float]] = {}
_WARMUP_N = 10


def _reset_accumulator(node_id: str):
    _S_high[node_id] = 0.0
    _S_low[node_id]  = 0.0


def update(node_id: str, value: float, tick: int) -> Optional[CUSUMAlert]:
    """
    Feed one observation. Returns CUSUMAlert if threshold crossed, else None.
    """
    # Warmup phase: collect first WARMUP_N observations to estimate mu, sigma
    if node_id not in _mu:
        if node_id not in _warmup:
            _warmup[node_id] = []
        _warmup[node_id].append(value)
        if len(_warmup[node_id]) >= _WARMUP_N:
            vals = _warmup.pop(node_id)
            _mu[node_id]    = sum(vals) / len(vals)
            var             = sum((v - _mu[node_id]) ** 2 for v in vals) / len(vals)
            _sigma[node_id] = max(var ** 0.5, 1e-6)
            _reset_accumulator(node_id)
        return None

    mu    = _mu[node_id]
    sigma = _sigma[node_id]
    k     = config.CUSUM_K
    h     = config.CUSUM_H

    z = (value - mu) / sigma

    _S_high[node_id] = max(0.0, _S_high.get(node_id, 0.0) + z - k)
    _S_low[node_id]  = max(0.0, _S_low.get(node_id, 0.0)  - z - k)

    if _S_high[node_id] > h:
        acc = _S_high[node_id]
        _reset_accumulator(node_id)
        return CUSUMAlert(node_id=node_id, direction="HIGH", tick=tick, value=value, accumulator_value=acc)

    if _S_low[node_id] > h:
        acc = _S_low[node_id]
        _reset_accumulator(node_id)
        return CUSUMAlert(node_id=node_id, direction="LOW", tick=tick, value=value, accumulator_value=acc)

    return None


def process_tick(clean_readings, tick: int) -> List[CUSUMAlert]:
    """Process all readings for one tick, return any alerts."""
    alerts: List[CUSUMAlert] = []
    for reading in clean_readings:
        if reading.subsystem == "traffic":
            continue  # exclude synthetic traffic from CUSUM
        alert = update(reading.node_id, reading.value, tick)
        if alert:
            alerts.append(alert)
    return alerts


def reset_all():
    _S_high.clear()
    _S_low.clear()
    _mu.clear()
    _sigma.clear()
    _warmup.clear()
