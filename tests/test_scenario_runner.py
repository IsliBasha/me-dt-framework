"""
Ticket 1 — Scenario Scripting & Replay Engine tests.
Verifies script loading, validation, listing, and execution hooks.
"""

import json
import os
import tempfile

import pytest

from attacks.scenario_runner import (
    load_script,
    list_scripts,
    ScriptValidationError,
    SCRIPTS_DIR,
)


# ---------------------------------------------------------------------------
# SCRIPTS_DIR
# ---------------------------------------------------------------------------

class TestScriptsDir:

    def test_scripts_dir_constant_exists(self):
        assert SCRIPTS_DIR is not None

    def test_scripts_dir_is_a_string(self):
        assert isinstance(SCRIPTS_DIR, str)


# ---------------------------------------------------------------------------
# load_script() — valid scripts
# ---------------------------------------------------------------------------

class TestLoadScript:

    def test_load_valid_json_script(self, tmp_path):
        script = [
            {"at_tick": 10, "scenario": "water_hammer"},
            {"at_tick": 20, "scenario": "load_redistribution"},
        ]
        f = tmp_path / "test_script.json"
        f.write_text(json.dumps(script))
        result = load_script(str(f))
        assert len(result) == 2
        assert result[0]["at_tick"] == 10
        assert result[0]["scenario"] == "water_hammer"

    def test_load_valid_yaml_script(self, tmp_path):
        yaml_content = "- at_tick: 5\n  scenario: actuator_hijack\n"
        f = tmp_path / "test_script.yaml"
        f.write_text(yaml_content)
        result = load_script(str(f))
        assert len(result) == 1
        assert result[0]["scenario"] == "actuator_hijack"

    def test_load_empty_script_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")
        assert load_script(str(f)) == []

    def test_loaded_entries_have_at_tick_and_scenario(self, tmp_path):
        script = [{"at_tick": 3, "scenario": "scada_replay"}]
        f = tmp_path / "s.json"
        f.write_text(json.dumps(script))
        entries = load_script(str(f))
        for entry in entries:
            assert "at_tick" in entry
            assert "scenario" in entry


# ---------------------------------------------------------------------------
# load_script() — validation errors
# ---------------------------------------------------------------------------

class TestLoadScriptValidation:

    def test_missing_at_tick_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps([{"scenario": "water_hammer"}]))
        with pytest.raises(ScriptValidationError):
            load_script(str(f))

    def test_missing_scenario_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps([{"at_tick": 5}]))
        with pytest.raises(ScriptValidationError):
            load_script(str(f))

    def test_negative_at_tick_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps([{"at_tick": -1, "scenario": "water_hammer"}]))
        with pytest.raises(ScriptValidationError):
            load_script(str(f))

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_script("/tmp/does_not_exist_xyz.json")

    def test_invalid_json_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json}")
        with pytest.raises(Exception):
            load_script(str(f))


# ---------------------------------------------------------------------------
# list_scripts()
# ---------------------------------------------------------------------------

class TestListScripts:

    def test_list_scripts_returns_list(self, tmp_path, monkeypatch):
        import attacks.scenario_runner as runner
        monkeypatch.setattr(runner, "SCRIPTS_DIR", str(tmp_path))
        result = list_scripts()
        assert isinstance(result, list)

    def test_list_scripts_finds_json_files(self, tmp_path, monkeypatch):
        import attacks.scenario_runner as runner
        monkeypatch.setattr(runner, "SCRIPTS_DIR", str(tmp_path))
        (tmp_path / "s1.json").write_text("[]")
        (tmp_path / "s2.json").write_text("[]")
        result = list_scripts()
        names = [r["name"] for r in result]
        assert "s1" in names
        assert "s2" in names

    def test_list_scripts_finds_yaml_files(self, tmp_path, monkeypatch):
        import attacks.scenario_runner as runner
        monkeypatch.setattr(runner, "SCRIPTS_DIR", str(tmp_path))
        (tmp_path / "demo.yaml").write_text("- at_tick: 1\n  scenario: water_hammer\n")
        result = list_scripts()
        names = [r["name"] for r in result]
        assert "demo" in names

    def test_list_scripts_includes_step_count(self, tmp_path, monkeypatch):
        import attacks.scenario_runner as runner
        monkeypatch.setattr(runner, "SCRIPTS_DIR", str(tmp_path))
        script = [{"at_tick": 1, "scenario": "w"}, {"at_tick": 2, "scenario": "x"}]
        (tmp_path / "two_step.json").write_text(json.dumps(script))
        result = list_scripts()
        entry = next(r for r in result if r["name"] == "two_step")
        assert entry["steps"] == 2

    def test_list_scripts_empty_dir(self, tmp_path, monkeypatch):
        import attacks.scenario_runner as runner
        monkeypatch.setattr(runner, "SCRIPTS_DIR", str(tmp_path))
        assert list_scripts() == []
