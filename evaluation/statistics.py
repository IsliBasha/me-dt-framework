"""
Ticket 2 — Statistics helpers for batch evaluation reports.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class StatsSummary:
    mean:    Optional[float]
    std:     Optional[float]
    count:   int
    min_val: Optional[float]
    max_val: Optional[float]


def compute_mean_std(values: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not values:
        return (None, None)
    n = len(values)
    mean = sum(values) / n
    if n == 1:
        return (mean, 0.0)
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return (mean, math.sqrt(variance))


def compute_ttd_stats(ttds: List[Optional[int]]) -> dict:
    valid = [t for t in ttds if t is not None]
    if not valid:
        return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
    mean, std = compute_mean_std([float(t) for t in valid])
    return {
        "count": len(valid),
        "mean":  mean,
        "std":   std,
        "min":   min(valid),
        "max":   max(valid),
    }
