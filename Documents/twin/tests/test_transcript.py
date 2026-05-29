"""
Ticket 3 — Mythos Transcript Pane & Audit Log tests.
"""

import asyncio
import json
import os

import pytest

import layers.layer4_mythos as layer4
from layers.layer4_mythos import get_recent_transcripts, reset_transcripts


@pytest.fixture(autouse=True)
def clean_deque():
    reset_transcripts()
    yield
    reset_transcripts()


@pytest.fixture
def no_audit_writes(monkeypatch):
    import utils.audit_log as audit_log
    monkeypatch.setattr(audit_log, "append_transcript", lambda r: None)


# ---------------------------------------------------------------------------
# In-memory deque tests (patch out audit writes to avoid disk I/O)
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("no_audit_writes")
class TestInMemoryDeque:

    def test_mock_mode_a_appends_transcript(self):
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=1))
        entries = get_recent_transcripts(10)
        assert len(entries) == 1
        e = entries[0]
        assert e["mode"] == "A"
        assert e["tick"] == 1
        assert e["latency_ms"] >= 0

    def test_mock_mode_b_appends_transcript(self):
        asyncio.run(layer4.run_mode_b({}, tick=5))
        entries = get_recent_transcripts(10)
        assert len(entries) == 1
        assert entries[0]["mode"] == "B"
        assert entries[0]["tick"] == 5

    def test_mock_mode_c_appends_transcript(self):
        asyncio.run(layer4.run_mode_c({}, [], [], tick=7))
        entries = get_recent_transcripts(10)
        assert len(entries) == 1
        assert entries[0]["mode"] == "C"
        assert entries[0]["tick"] == 7

    def test_get_recent_transcripts_respects_n(self):
        for i in range(5):
            asyncio.run(layer4.run_mode_a({}, [], [], [], tick=i))
        assert len(get_recent_transcripts(3)) == 3
        assert len(get_recent_transcripts(10)) == 5

    def test_transcript_deque_maxlen_is_50(self):
        for i in range(55):
            asyncio.run(layer4.run_mode_a({}, [], [], [], tick=i))
        assert len(get_recent_transcripts(100)) == 50

    def test_reset_transcripts_clears_deque(self):
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=1))
        reset_transcripts()
        assert get_recent_transcripts(10) == []

    def test_transcript_entry_has_required_fields(self):
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=42))
        e = get_recent_transcripts(1)[0]
        for field in ("id", "tick", "mode", "prompt", "response_raw", "parsed_result",
                      "latency_ms", "timestamp_iso"):
            assert field in e, f"Missing field: {field}"

    def test_transcript_ids_increment(self):
        for i in range(3):
            asyncio.run(layer4.run_mode_a({}, [], [], [], tick=i))
        ids = [e["id"] for e in get_recent_transcripts(10)]
        assert ids == sorted(ids)
        assert len(set(ids)) == 3

    def test_mixed_modes_all_captured(self):
        asyncio.run(layer4.run_mode_a({}, [], [], [], tick=1))
        asyncio.run(layer4.run_mode_b({}, tick=2))
        asyncio.run(layer4.run_mode_c({}, [], [], tick=3))
        entries = get_recent_transcripts(10)
        modes = {e["mode"] for e in entries}
        assert modes == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Audit log file tests (use real append_transcript)
# ---------------------------------------------------------------------------

class TestAuditLog:

    def test_audit_log_writes_jsonl(self, tmp_path, monkeypatch):
        import utils.audit_log as audit_log
        monkeypatch.setattr(audit_log, "_run_id", "test_run_t3")
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            audit_log.append_transcript({"tick": 1, "mode": "A", "prompt": "hello"})
            path = tmp_path / "reports" / "transcripts_test_run_t3.jsonl"
            assert path.exists(), f"File not created at {path}"
            data = json.loads(path.read_text().strip())
            assert data["tick"] == 1
        finally:
            os.chdir(original_cwd)

    def test_audit_log_appends_multiple(self, tmp_path, monkeypatch):
        import utils.audit_log as audit_log
        monkeypatch.setattr(audit_log, "_run_id", "test_run_t3b")
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            audit_log.append_transcript({"tick": 1, "mode": "A"})
            audit_log.append_transcript({"tick": 2, "mode": "B"})
            path = tmp_path / "reports" / "transcripts_test_run_t3b.jsonl"
            lines = [json.loads(l) for l in path.read_text().strip().splitlines()]
            assert len(lines) == 2
            assert lines[1]["mode"] == "B"
        finally:
            os.chdir(original_cwd)
