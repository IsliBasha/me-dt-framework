"""
Ticket 2 — Batch Evaluation Harness tests.
Verifies batch_runner module structure, RunResult dataclass,
statistics computation, and report generation.
"""

import os
import pytest

from evaluation.batch_runner import RunResult, run_scenario, aggregate_results
from evaluation.statistics import (
    compute_mean_std,
    compute_ttd_stats,
    StatsSummary,
)


# ---------------------------------------------------------------------------
# RunResult dataclass
# ---------------------------------------------------------------------------

class TestRunResult:

    def test_run_result_has_required_fields(self):
        r = RunResult(
            run_id=0,
            scenario="water_hammer",
            seed=42,
            me_dt_detected=True,
            cusum_detected=False,
            isoforest_detected=True,
            me_dt_ttd=5,
            cusum_ttd=None,
            isoforest_ttd=8,
        )
        assert r.run_id == 0
        assert r.scenario == "water_hammer"
        assert r.me_dt_detected is True
        assert r.cusum_detected is False
        assert r.me_dt_ttd == 5

    def test_run_result_ttd_can_be_none(self):
        r = RunResult(
            run_id=1, scenario="scada_replay", seed=1,
            me_dt_detected=False, cusum_detected=False, isoforest_detected=False,
            me_dt_ttd=None, cusum_ttd=None, isoforest_ttd=None,
        )
        assert r.me_dt_ttd is None


# ---------------------------------------------------------------------------
# run_scenario()
# ---------------------------------------------------------------------------

class TestRunScenario:

    def test_run_scenario_returns_run_result(self):
        result = run_scenario("water_hammer", seed=0, max_ticks=30)
        assert isinstance(result, RunResult)

    def test_run_scenario_sets_scenario_name(self):
        result = run_scenario("load_redistribution", seed=1, max_ticks=30)
        assert result.scenario == "load_redistribution"

    def test_run_scenario_sets_seed(self):
        result = run_scenario("water_hammer", seed=99, max_ticks=30)
        assert result.seed == 99

    def test_run_scenario_deterministic_with_same_seed(self):
        r1 = run_scenario("water_hammer", seed=7, max_ticks=30)
        r2 = run_scenario("water_hammer", seed=7, max_ticks=30)
        assert r1.me_dt_detected == r2.me_dt_detected

    def test_run_scenario_different_seeds_may_differ(self):
        r1 = run_scenario("water_hammer", seed=0, max_ticks=30)
        r2 = run_scenario("water_hammer", seed=1, max_ticks=30)
        assert isinstance(r1, RunResult)
        assert isinstance(r2, RunResult)


# ---------------------------------------------------------------------------
# aggregate_results()
# ---------------------------------------------------------------------------

class TestAggregateResults:

    def _make_results(self):
        return [
            RunResult(0, "water_hammer", 0, True,  True,  False, 3, 5,    None),
            RunResult(1, "water_hammer", 1, True,  False, True,  4, None, 7),
            RunResult(2, "water_hammer", 2, False, False, False, None, None, None),
        ]

    def test_aggregate_returns_dict(self):
        results = self._make_results()
        agg = aggregate_results(results)
        assert isinstance(agg, dict)

    def test_aggregate_has_detection_rates(self):
        results = self._make_results()
        agg = aggregate_results(results)
        assert "me_dt_detection_rate" in agg
        assert "cusum_detection_rate" in agg
        assert "isoforest_detection_rate" in agg

    def test_aggregate_detection_rate_correct(self):
        results = self._make_results()
        agg = aggregate_results(results)
        assert abs(agg["me_dt_detection_rate"] - 2/3) < 0.01

    def test_aggregate_has_mean_ttd(self):
        results = self._make_results()
        agg = aggregate_results(results)
        assert "me_dt_mean_ttd" in agg

    def test_aggregate_mean_ttd_ignores_none(self):
        results = self._make_results()
        agg = aggregate_results(results)
        # ME-DT TTDs: 3, 4 (None excluded) → mean = 3.5
        assert abs(agg["me_dt_mean_ttd"] - 3.5) < 0.01


# ---------------------------------------------------------------------------
# statistics helpers
# ---------------------------------------------------------------------------

class TestStatisticsHelpers:

    def test_compute_mean_std_basic(self):
        mean, std = compute_mean_std([2.0, 4.0, 6.0])
        assert abs(mean - 4.0) < 0.001

    def test_compute_mean_std_empty_returns_none(self):
        result = compute_mean_std([])
        assert result == (None, None)

    def test_compute_mean_std_single_value(self):
        mean, std = compute_mean_std([5.0])
        assert mean == 5.0

    def test_compute_ttd_stats_filters_none(self):
        ttds = [3, None, 5, None, 7]
        stats = compute_ttd_stats(ttds)
        assert stats["count"] == 3
        assert abs(stats["mean"] - 5.0) < 0.001

    def test_stats_summary_dataclass(self):
        s = StatsSummary(mean=1.0, std=0.5, count=10, min_val=0.5, max_val=2.0)
        assert s.mean == 1.0
        assert s.count == 10
