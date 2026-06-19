"""
Ticket 8 — TTD & Confusion Matrix backend tests.
Verifies that get_summary() returns per-detector confusion matrix counts
including TN/FN inferred from clean-period tick counts.
"""

import pytest
import utils.metrics as metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics.reset()
    yield
    metrics.reset()


# ---------------------------------------------------------------------------
# Confusion matrix fields in summary
# ---------------------------------------------------------------------------

class TestConfusionMatrixFields:

    def test_summary_has_confusion_matrix_key(self):
        summary = metrics.get_summary()
        assert "confusion_matrix" in summary

    def test_confusion_matrix_has_all_detectors(self):
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        for det in ("ME-DT", "CUSUM", "ISOFOREST"):
            assert det in cm

    def test_confusion_matrix_has_tp_fp_tn_fn(self):
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        for det, counts in cm.items():
            for field in ("TP", "FP", "TN", "FN"):
                assert field in counts, f"{det} missing {field}"

    def test_initial_all_counts_zero_except_tn(self):
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        for det in ("ME-DT", "CUSUM", "ISOFOREST"):
            assert cm[det]["TP"] == 0
            assert cm[det]["FP"] == 0
            assert cm[det]["FN"] == 0
            # TN = clean_period_end - 0 FPs = 20
            assert cm[det]["TN"] == 20


# ---------------------------------------------------------------------------
# TP/FP propagate from existing tracking
# ---------------------------------------------------------------------------

class TestTPFPPropagation:

    def test_tp_recorded_after_detection_in_window(self):
        metrics.record_injection("water_hammer", tick=5)
        metrics.record_detection("ME-DT", "water_hammer", tick=8)
        cm = metrics.get_summary()["confusion_matrix"]
        assert cm["ME-DT"]["TP"] == 1

    def test_fp_recorded_for_clean_period_alert(self):
        metrics.record_detection("CUSUM", None, tick=3)  # tick 3 <= clean_period_end=20
        cm = metrics.get_summary()["confusion_matrix"]
        assert cm["CUSUM"]["FP"] == 1


# ---------------------------------------------------------------------------
# FN: injection occurred but detector never fired within window
# ---------------------------------------------------------------------------

class TestFalseNegative:

    def test_fn_when_injection_not_detected(self):
        metrics.record_injection("load_redistribution", tick=5)
        metrics.set_clean_period_end(100)
        cm = metrics.get_summary()["confusion_matrix"]
        assert cm["ME-DT"]["FN"] == 1
        assert cm["CUSUM"]["FN"] == 1
        assert cm["ISOFOREST"]["FN"] == 1

    def test_fn_zero_when_all_detectors_fire(self):
        metrics.record_injection("water_hammer", tick=5)
        metrics.record_detection("ME-DT", "water_hammer", tick=6)
        metrics.record_detection("CUSUM", "water_hammer", tick=7)
        metrics.record_detection("ISOFOREST", "water_hammer", tick=8)
        cm = metrics.get_summary()["confusion_matrix"]
        assert cm["ME-DT"]["FN"] == 0
        assert cm["CUSUM"]["FN"] == 0
        assert cm["ISOFOREST"]["FN"] == 0


# ---------------------------------------------------------------------------
# TN: clean ticks where no alert fired
# ---------------------------------------------------------------------------

class TestTrueNegative:

    def test_tn_counts_clean_ticks_with_no_alert(self):
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        for det in ("ME-DT", "CUSUM", "ISOFOREST"):
            assert cm[det]["TN"] >= 0

    def test_tn_decreases_by_one_per_fp(self):
        initial_tn = metrics.get_summary()["confusion_matrix"]["ME-DT"]["TN"]
        metrics.record_detection("ME-DT", None, tick=2)  # FP in clean period
        new_tn = metrics.get_summary()["confusion_matrix"]["ME-DT"]["TN"]
        assert new_tn == initial_tn - 1


# ---------------------------------------------------------------------------
# set_clean_period_end
# ---------------------------------------------------------------------------

class TestSetCleanPeriodEnd:

    def test_set_clean_period_end_exists(self):
        assert hasattr(metrics, "set_clean_period_end")

    def test_set_clean_period_end_changes_tn_base(self):
        metrics.set_clean_period_end(50)
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        assert cm["ME-DT"]["TN"] == 50

    def test_reset_restores_default_clean_period(self):
        metrics.set_clean_period_end(100)
        metrics.reset()
        summary = metrics.get_summary()
        cm = summary["confusion_matrix"]
        assert cm["ME-DT"]["TN"] == 20
