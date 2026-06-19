"""
Ticket 5 — Mode A Response Cache tests.
Verifies cache hit/miss logic, TTL expiry, hit-rate tracking, and config flags.
"""

import asyncio
import pytest

import config
import layers.layer4_mythos as layer4
from layers.layer4_mythos import (
    reset_transcripts,
    get_cache_stats,
    reset_cache,
)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    import utils.audit_log as audit_log
    monkeypatch.setattr(audit_log, "append_transcript", lambda r: None)
    reset_transcripts()
    reset_cache()
    yield
    reset_transcripts()
    reset_cache()


# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------

class TestCacheConfig:

    def test_cache_ttl_constant_exists(self):
        assert hasattr(config, "MODE_A_CACHE_TTL_TICKS")

    def test_cache_enabled_constant_exists(self):
        assert hasattr(config, "MODE_A_CACHE_ENABLED")

    def test_cache_ttl_is_positive(self):
        assert config.MODE_A_CACHE_TTL_TICKS > 0

    def test_cache_enabled_is_bool(self):
        assert isinstance(config.MODE_A_CACHE_ENABLED, bool)


# ---------------------------------------------------------------------------
# get_cache_stats() baseline
# ---------------------------------------------------------------------------

class TestCacheStats:

    def test_initial_stats_are_zero(self):
        stats = get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_initial_hit_rate_is_zero(self):
        stats = get_cache_stats()
        assert stats["hit_rate"] == 0.0

    def test_reset_cache_clears_stats(self):
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=1))
        reset_cache()
        stats = get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


# ---------------------------------------------------------------------------
# Cache miss → hit on identical input
# ---------------------------------------------------------------------------

class TestCacheBehavior:

    def test_first_call_is_always_a_miss(self):
        asyncio.run(layer4.run_mode_a({"water": {}}, [], [], [], tick=10))
        stats = get_cache_stats()
        assert stats["misses"] >= 1

    def test_identical_state_produces_cache_hit(self):
        state = {"water": {"10": {"value": 42.0}}}
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=10))
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=11))
        stats = get_cache_stats()
        assert stats["hits"] >= 1

    def test_changed_violations_causes_cache_miss(self):
        state = {"water": {"10": {"value": 42.0}}}
        v1 = [{"rule_id": "W1", "severity": "HIGH"}]
        v2 = [{"rule_id": "W2", "severity": "HIGH"}]
        asyncio.run(layer4.run_mode_a(state, v1, [], [], tick=10))
        asyncio.run(layer4.run_mode_a(state, v2, [], [], tick=11))
        stats = get_cache_stats()
        assert stats["misses"] >= 2

    def test_hit_rate_calculation(self):
        state = {"water": {"10": {"value": 1.0}}}
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=1))  # miss
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=2))  # hit
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=3))  # hit
        stats = get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert abs(stats["hit_rate"] - 2/3) < 0.01

    def test_cache_hit_returns_same_result(self):
        state = {"water": {"10": {"value": 5.0}}}
        r1 = asyncio.run(layer4.run_mode_a(state, [], [], [], tick=1))
        r2 = asyncio.run(layer4.run_mode_a(state, [], [], [], tick=2))
        assert r1.threat_class == r2.threat_class
        assert r1.confidence == r2.confidence


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

class TestCacheTTL:

    def test_cache_expires_after_ttl(self):
        state = {"water": {"10": {"value": 9.0}}}
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=1))
        expire_tick = 1 + config.MODE_A_CACHE_TTL_TICKS + 1
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=expire_tick))
        stats = get_cache_stats()
        assert stats["misses"] >= 2

    def test_cache_hit_within_ttl_window(self):
        state = {"water": {"10": {"value": 9.0}}}
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=1))
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=2))
        stats = get_cache_stats()
        assert stats["hits"] >= 1


# ---------------------------------------------------------------------------
# Cache disabled via config
# ---------------------------------------------------------------------------

class TestCacheDisable:

    def test_when_disabled_always_misses(self, monkeypatch):
        monkeypatch.setattr(config, "MODE_A_CACHE_ENABLED", False)
        state = {"water": {"10": {"value": 3.0}}}
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=1))
        asyncio.run(layer4.run_mode_a(state, [], [], [], tick=2))
        stats = get_cache_stats()
        assert stats["hits"] == 0
