"""
Ticket 7 — Persistent Vulnerability Atlas tests.
Verifies VulnerabilityAtlas deduplication, ranking, persistence, and scoring.
"""

import json
import os
import pytest

from layers.atlas import VulnerabilityAtlas


@pytest.fixture
def atlas(tmp_path):
    return VulnerabilityAtlas(persist_path=str(tmp_path / "atlas.jsonl"))


def _make_entry(**kwargs):
    defaults = {
        "entry_point": "J10/water",
        "attack_steps": [{"step": 1, "action": "Inject", "target_node": "J10", "expected_effect": "Pressure drop"}],
        "physical_consequence": "Service disruption",
        "detection_difficulty": "HIGH",
        "evasion_rationale": "Sub-threshold changes",
        "estimated_impact_severity": 7,
        "tick": 5,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Basic add and retrieve
# ---------------------------------------------------------------------------

class TestAtlasBasics:

    def test_initial_atlas_is_empty(self, atlas):
        assert atlas.all() == []

    def test_add_entry_returns_path_count(self, atlas):
        atlas.add(_make_entry())
        assert len(atlas.all()) == 1

    def test_add_multiple_entries(self, atlas):
        atlas.add(_make_entry(entry_point="J1/water"))
        atlas.add(_make_entry(
            entry_point="bus_5/power",
            attack_steps=[{"step": 1, "action": "Overload", "target_node": "bus_5", "expected_effect": "Voltage drop"}]
        ))
        assert len(atlas.all()) == 2

    def test_all_returns_list_of_dicts(self, atlas):
        atlas.add(_make_entry())
        result = atlas.all()
        assert isinstance(result, list)
        assert isinstance(result[0], dict)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:

    def test_duplicate_entry_point_and_first_step_is_deduplicated(self, atlas):
        e1 = _make_entry(entry_point="J10/water", attack_steps=[
            {"step": 1, "action": "FDI", "target_node": "J10", "expected_effect": "Pressure"}
        ])
        e2 = _make_entry(entry_point="J10/water", attack_steps=[
            {"step": 1, "action": "FDI", "target_node": "J10", "expected_effect": "Different effect"}
        ], estimated_impact_severity=9)
        atlas.add(e1)
        atlas.add(e2)
        assert len(atlas.all()) == 1

    def test_different_first_action_is_not_deduplicated(self, atlas):
        e1 = _make_entry(entry_point="J10/water", attack_steps=[
            {"step": 1, "action": "FDI", "target_node": "J10", "expected_effect": "Pressure"}
        ])
        e2 = _make_entry(entry_point="J10/water", attack_steps=[
            {"step": 1, "action": "HAMMER", "target_node": "J10", "expected_effect": "Surge"}
        ])
        atlas.add(e1)
        atlas.add(e2)
        assert len(atlas.all()) == 2

    def test_different_entry_point_is_not_deduplicated(self, atlas):
        atlas.add(_make_entry(entry_point="J1/water"))
        atlas.add(_make_entry(entry_point="J2/water"))
        assert len(atlas.all()) == 2


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

class TestRanking:

    def test_ranked_returns_sorted_list(self, atlas):
        atlas.add(_make_entry(estimated_impact_severity=5, detection_difficulty="HIGH"))
        atlas.add(_make_entry(
            entry_point="J2/water",
            attack_steps=[{"step": 1, "action": "X", "target_node": "J2", "expected_effect": "y"}],
            estimated_impact_severity=9, detection_difficulty="LOW"
        ))
        ranked = atlas.ranked()
        assert isinstance(ranked, list)
        assert len(ranked) == 2

    def test_higher_severity_lower_difficulty_ranks_first(self, atlas):
        low_risk = _make_entry(
            entry_point="J1/water",
            attack_steps=[{"step": 1, "action": "A", "target_node": "J1", "expected_effect": "x"}],
            estimated_impact_severity=3, detection_difficulty="HIGH",
        )
        high_risk = _make_entry(
            entry_point="J2/water",
            attack_steps=[{"step": 1, "action": "B", "target_node": "J2", "expected_effect": "y"}],
            estimated_impact_severity=9, detection_difficulty="LOW",
        )
        atlas.add(low_risk)
        atlas.add(high_risk)
        ranked = atlas.ranked()
        assert ranked[0]["entry_point"] == "J2/water"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    def test_entries_are_written_to_jsonl(self, tmp_path):
        path = str(tmp_path / "atlas.jsonl")
        a = VulnerabilityAtlas(persist_path=path)
        a.add(_make_entry())
        assert os.path.exists(path)
        with open(path) as f:
            lines = [json.loads(l) for l in f.read().strip().splitlines()]
        assert len(lines) == 1

    def test_loading_from_existing_jsonl(self, tmp_path):
        path = str(tmp_path / "atlas.jsonl")
        entry = _make_entry()
        with open(path, "w") as f:
            f.write(json.dumps(entry) + "\n")
        a = VulnerabilityAtlas(persist_path=path)
        assert len(a.all()) == 1

    def test_persistence_deduplication_on_reload(self, tmp_path):
        path = str(tmp_path / "atlas.jsonl")
        a1 = VulnerabilityAtlas(persist_path=path)
        a1.add(_make_entry(entry_point="J10/water"))
        a2 = VulnerabilityAtlas(persist_path=path)
        a2.add(_make_entry(entry_point="J10/water"))
        assert len(a2.all()) == 1


# ---------------------------------------------------------------------------
# Score attribute
# ---------------------------------------------------------------------------

class TestScoring:

    def test_ranked_entries_have_score_field(self, atlas):
        atlas.add(_make_entry())
        ranked = atlas.ranked()
        assert "score" in ranked[0]

    def test_score_is_positive_float(self, atlas):
        atlas.add(_make_entry(estimated_impact_severity=8, detection_difficulty="HIGH"))
        ranked = atlas.ranked()
        assert ranked[0]["score"] > 0
