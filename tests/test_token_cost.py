"""
Ticket 4 — Token & Cost Meter tests.
Verifies token accumulation, USD cost calculation, per-mode breakdown,
and that reset() clears everything.
"""

import asyncio
import pytest

import config
import utils.metrics as metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture
def no_audit_writes(monkeypatch):
    import utils.audit_log as audit_log
    monkeypatch.setattr(audit_log, "append_transcript", lambda r: None)


# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------

class TestPriceConstants:

    def test_input_price_constant_exists(self):
        assert hasattr(config, "ANTHROPIC_PRICE_PER_MTOK_INPUT")

    def test_output_price_constant_exists(self):
        assert hasattr(config, "ANTHROPIC_PRICE_PER_MTOK_OUTPUT")

    def test_input_price_is_positive(self):
        assert config.ANTHROPIC_PRICE_PER_MTOK_INPUT > 0

    def test_output_price_is_positive(self):
        assert config.ANTHROPIC_PRICE_PER_MTOK_OUTPUT > 0


# ---------------------------------------------------------------------------
# record_token_usage() accumulation
# ---------------------------------------------------------------------------

class TestRecordTokenUsage:

    def test_initial_summary_has_zero_tokens(self):
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_input_tokens"] == 0
        assert summary["token_usage"]["total_output_tokens"] == 0

    def test_initial_cost_is_zero(self):
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_cost_usd"] == 0.0

    def test_single_record_accumulates(self):
        metrics.record_token_usage("A", in_tokens=100, out_tokens=50)
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_input_tokens"] == 100
        assert summary["token_usage"]["total_output_tokens"] == 50

    def test_multiple_records_sum_correctly(self):
        metrics.record_token_usage("A", in_tokens=100, out_tokens=50)
        metrics.record_token_usage("B", in_tokens=200, out_tokens=80)
        metrics.record_token_usage("C", in_tokens=150, out_tokens=60)
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_input_tokens"] == 450
        assert summary["token_usage"]["total_output_tokens"] == 190

    def test_cost_calculation_correct(self):
        # 1_000_000 input tokens at INPUT price = INPUT price in USD
        metrics.record_token_usage("A", in_tokens=1_000_000, out_tokens=0)
        summary = metrics.get_summary()
        expected = config.ANTHROPIC_PRICE_PER_MTOK_INPUT
        assert abs(summary["token_usage"]["total_cost_usd"] - expected) < 0.001

    def test_output_cost_calculation_correct(self):
        metrics.record_token_usage("A", in_tokens=0, out_tokens=1_000_000)
        summary = metrics.get_summary()
        expected = config.ANTHROPIC_PRICE_PER_MTOK_OUTPUT
        assert abs(summary["token_usage"]["total_cost_usd"] - expected) < 0.001

    def test_cost_accumulates_across_calls(self):
        metrics.record_token_usage("A", in_tokens=500_000, out_tokens=250_000)
        metrics.record_token_usage("B", in_tokens=500_000, out_tokens=250_000)
        summary = metrics.get_summary()
        expected = (
            1_000_000 * config.ANTHROPIC_PRICE_PER_MTOK_INPUT / 1_000_000
            + 500_000 * config.ANTHROPIC_PRICE_PER_MTOK_OUTPUT / 1_000_000
        )
        assert abs(summary["token_usage"]["total_cost_usd"] - expected) < 0.001

    def test_reset_clears_token_counts(self):
        metrics.record_token_usage("A", in_tokens=999, out_tokens=111)
        metrics.reset()
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_input_tokens"] == 0
        assert summary["token_usage"]["total_output_tokens"] == 0

    def test_reset_clears_cost(self):
        metrics.record_token_usage("A", in_tokens=999_999, out_tokens=111_111)
        metrics.reset()
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# Per-mode breakdown
# ---------------------------------------------------------------------------

class TestPerModeBreakdown:

    def test_summary_has_mode_breakdown(self):
        metrics.record_token_usage("A", in_tokens=100, out_tokens=50)
        summary = metrics.get_summary()
        assert "by_mode" in summary["token_usage"]

    def test_mode_a_tracked_separately(self):
        metrics.record_token_usage("A", in_tokens=100, out_tokens=50)
        metrics.record_token_usage("B", in_tokens=200, out_tokens=80)
        summary = metrics.get_summary()
        assert summary["token_usage"]["by_mode"]["A"]["input_tokens"] == 100
        assert summary["token_usage"]["by_mode"]["B"]["input_tokens"] == 200

    def test_mode_c_tracked_separately(self):
        metrics.record_token_usage("C", in_tokens=300, out_tokens=90)
        summary = metrics.get_summary()
        assert summary["token_usage"]["by_mode"]["C"]["input_tokens"] == 300
        assert summary["token_usage"]["by_mode"]["C"]["output_tokens"] == 90

    def test_mode_breakdown_defaults_to_zero_for_unused_modes(self):
        metrics.record_token_usage("A", in_tokens=50, out_tokens=25)
        summary = metrics.get_summary()
        assert summary["token_usage"]["by_mode"].get("B", {}).get("input_tokens", 0) == 0


# ---------------------------------------------------------------------------
# Mock path does not record tokens (no API key → no usage)
# ---------------------------------------------------------------------------

class TestMockPathTokens:

    @pytest.mark.usefixtures("no_audit_writes")
    def test_mock_mode_a_does_not_record_tokens(self):
        import layers.layer4_mythos as layer4
        from layers.layer4_mythos import reset_transcripts
        reset_transcripts()
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=1))
        summary = metrics.get_summary()
        assert summary["token_usage"]["total_input_tokens"] == 0
