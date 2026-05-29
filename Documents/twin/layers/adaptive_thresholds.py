"""
Attack-adaptive detector thresholds.

On SANDBOX or QUARANTINE tier confirmation, tighten CUSUM h for affected nodes
and raise IsoForest contamination so detectors become more sensitive in the
neighborhood of an ongoing attack. MONITOR tier makes no changes.
"""

from typing import List
import config
import baselines.cusum_detector as _cusum
import baselines.isolation_forest as _iso
from layers.response_tiers import ResponseTier

_SANDBOX_CUSUM_H = 2.5
_QUARANTINE_CUSUM_H = 1.5
_SANDBOX_CONTAMINATION_BUMP = 0.05
_QUARANTINE_CONTAMINATION_BUMP = 0.10
_MAX_CONTAMINATION = 0.45


def tighten_on_confirmed_attack(node_ids: List[str], tier: ResponseTier) -> None:
    """Tighten detector thresholds for the given nodes based on confirmed tier."""
    if tier == ResponseTier.SANDBOX:
        for node_id in node_ids:
            _cusum.set_node_threshold(node_id, _SANDBOX_CUSUM_H)
        new_contamination = min(
            _iso.get_contamination() + _SANDBOX_CONTAMINATION_BUMP,
            _MAX_CONTAMINATION,
        )
        _iso.set_contamination(new_contamination)

    elif tier == ResponseTier.QUARANTINE:
        for node_id in node_ids:
            _cusum.set_node_threshold(node_id, _QUARANTINE_CUSUM_H)
        new_contamination = min(
            _iso.get_contamination() + _QUARANTINE_CONTAMINATION_BUMP,
            _MAX_CONTAMINATION,
        )
        _iso.set_contamination(new_contamination)


def reset_overrides() -> None:
    """Restore all detector thresholds to config defaults."""
    _cusum.reset_all()
    _iso.reset()
