"""
Isolation Forest Detector — Liu et al. (2008).
sklearn.ensemble.IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
Retrained every ISOFOREST_RETRAIN_INTERVAL ticks on the rolling window.
NOTE: Synthetic traffic excluded from feature vector (documented choice).
"""

from typing import List, Optional
import numpy as np

import config
from models.state_vector import IsoForestAlert, NodeReading

try:
    from sklearn.ensemble import IsolationForest as _IsoForest
    _SKLEARN_OK = True
except ImportError:
    _SKLEARN_OK = False
    print("[IsoForest] WARNING: scikit-learn not installed")

_model = None
_feature_buffer: List[np.ndarray] = []
_fitted_at_tick: int = -1
_active_contamination: float = config.ISOFOREST_CONTAMINATION


def set_contamination(contamination: float) -> None:
    """Override the contamination used for the next model fit (clamped to (0, 0.5])."""
    global _active_contamination
    _active_contamination = max(1e-4, min(contamination, 0.5))


def get_contamination() -> float:
    """Return the currently active contamination value."""
    return _active_contamination


def _build_feature_vector(clean_readings: List[NodeReading]) -> Optional[np.ndarray]:
    """Concatenate numeric values from water + power nodes only."""
    feats = []
    for r in clean_readings:
        if r.subsystem in ("water", "power") and r.metric != "pump_status" and isinstance(r.value, (int, float)):
            feats.append(float(r.value))
    if not feats:
        return None
    return np.array(feats, dtype=np.float32)


def process_tick(clean_readings: List[NodeReading], tick: int) -> Optional[IsoForestAlert]:
    global _model, _fitted_at_tick
    if not _SKLEARN_OK:
        return None

    vec = _build_feature_vector(clean_readings)
    if vec is None:
        return None

    _feature_buffer.append(vec)

    # Trim buffer to rolling window
    max_buf = config.STATE_HISTORY_WINDOW
    if len(_feature_buffer) > max_buf:
        _feature_buffer.pop(0)

    # Fit or refit periodically
    should_fit = (
        _model is None and len(_feature_buffer) >= 20
    ) or (
        tick > 0 and tick % config.ISOFOREST_RETRAIN_INTERVAL == 0
        and len(_feature_buffer) >= 20
    )

    if should_fit:
        try:
            # Pad to uniform length
            max_len = max(len(v) for v in _feature_buffer)
            X = np.array([
                np.pad(v, (0, max_len - len(v))) for v in _feature_buffer
            ], dtype=np.float32)
            _model = _IsoForest(
                n_estimators=100,
                contamination=_active_contamination,
                random_state=42,
            )
            _model.fit(X)
            _fitted_at_tick = tick
        except Exception as e:
            print(f"[IsoForest] Fit error at tick {tick}: {e}")
            return None

    if _model is None:
        return None

    # Predict
    try:
        max_len = max(len(v) for v in _feature_buffer)
        x = np.pad(vec, (0, max_len - len(vec))).reshape(1, -1)
        score = float(_model.decision_function(x)[0])
    except Exception:
        return None

    if score < -0.1:
        return IsoForestAlert(
            tick=tick,
            anomaly_score=round(score, 4),
            feature_vector_norm=float(np.linalg.norm(vec)),
        )
    return None


def reset():
    global _model, _fitted_at_tick, _active_contamination
    _model = None
    _fitted_at_tick = -1
    _active_contamination = config.ISOFOREST_CONTAMINATION
    _feature_buffer.clear()
