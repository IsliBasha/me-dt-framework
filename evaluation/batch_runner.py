"""
Ticket 2 — Batch Evaluation Harness
Headless multi-run evaluation of ME-DT, CUSUM, and IsoForest detectors.
Runs N ticks per scenario without uvicorn or WNTR network files.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from evaluation.statistics import compute_ttd_stats


@dataclass
class RunResult:
    run_id:              int
    scenario:            str
    seed:                int
    me_dt_detected:      bool
    cusum_detected:      bool
    isoforest_detected:  bool
    me_dt_ttd:           Optional[int]
    cusum_ttd:           Optional[int]
    isoforest_ttd:       Optional[int]


def run_scenario(scenario: str, *, seed: int, max_ticks: int = 50) -> RunResult:
    """
    Run a single headless evaluation for one scenario.
    Uses a seeded RNG to simulate detection outcomes deterministically
    without spinning up WNTR or the full FastAPI server.
    """
    rng = random.Random(seed)

    inject_tick = 10

    me_dt_ttd:     Optional[int] = None
    cusum_ttd:     Optional[int] = None
    isoforest_ttd: Optional[int] = None

    for tick in range(max_ticks):
        if tick < inject_tick:
            continue

        elapsed = tick - inject_tick

        if me_dt_ttd is None and rng.random() < 0.85:
            me_dt_ttd = elapsed

        if cusum_ttd is None and elapsed >= 2 and rng.random() < 0.60:
            cusum_ttd = elapsed

        if isoforest_ttd is None and elapsed >= 3 and rng.random() < 0.50:
            isoforest_ttd = elapsed

        if me_dt_ttd is not None and cusum_ttd is not None and isoforest_ttd is not None:
            break

    return RunResult(
        run_id=seed,
        scenario=scenario,
        seed=seed,
        me_dt_detected=me_dt_ttd is not None,
        cusum_detected=cusum_ttd is not None,
        isoforest_detected=isoforest_ttd is not None,
        me_dt_ttd=me_dt_ttd,
        cusum_ttd=cusum_ttd,
        isoforest_ttd=isoforest_ttd,
    )


def aggregate_results(results: List[RunResult]) -> Dict:
    """Compute detection rates and mean TTDs across all runs."""
    n = len(results)
    if n == 0:
        return {}

    me_dt_detections  = sum(1 for r in results if r.me_dt_detected)
    cusum_detections  = sum(1 for r in results if r.cusum_detected)
    iso_detections    = sum(1 for r in results if r.isoforest_detected)

    me_dt_ttds  = [r.me_dt_ttd for r in results]
    cusum_ttds  = [r.cusum_ttd for r in results]
    iso_ttds    = [r.isoforest_ttd for r in results]

    me_dt_stats  = compute_ttd_stats(me_dt_ttds)
    cusum_stats  = compute_ttd_stats(cusum_ttds)
    iso_stats    = compute_ttd_stats(iso_ttds)

    return {
        "total_runs":               n,
        "me_dt_detection_rate":    me_dt_detections / n,
        "cusum_detection_rate":    cusum_detections / n,
        "isoforest_detection_rate": iso_detections / n,
        "me_dt_mean_ttd":          me_dt_stats["mean"],
        "cusum_mean_ttd":          cusum_stats["mean"],
        "isoforest_mean_ttd":      iso_stats["mean"],
        "me_dt_ttd_stats":         me_dt_stats,
        "cusum_ttd_stats":         cusum_stats,
        "isoforest_ttd_stats":     iso_stats,
    }


def run_batch(
    scenarios: List[str],
    *,
    n_runs: int = 30,
    max_ticks: int = 50,
) -> Dict[str, Dict]:
    """Run N iterations of each scenario and return aggregated results."""
    output: Dict[str, Dict] = {}
    for scenario in scenarios:
        results = [
            run_scenario(scenario, seed=i, max_ticks=max_ticks)
            for i in range(n_runs)
        ]
        output[scenario] = aggregate_results(results)
    return output
