"""
Tests for per-threat-class playbooks.
RED: all tests fail until layers/playbooks.py is created.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestPlaybookStructure(unittest.TestCase):
    """PLAYBOOKS dict must be importable and well-formed."""

    def setUp(self):
        from layers.playbooks import PLAYBOOKS, PlaybookStep
        self.PLAYBOOKS = PLAYBOOKS
        self.PlaybookStep = PlaybookStep

    def test_playbooks_dict_is_not_empty(self):
        self.assertGreater(len(self.PLAYBOOKS), 0)

    def test_water_hammer_playbook_exists(self):
        self.assertIn("water_hammer", self.PLAYBOOKS)

    def test_load_redistribution_playbook_exists(self):
        self.assertIn("load_redistribution", self.PLAYBOOKS)

    def test_scada_replay_playbook_exists(self):
        self.assertIn("scada_replay", self.PLAYBOOKS)

    def test_each_playbook_has_at_least_one_step(self):
        for threat_class, steps in self.PLAYBOOKS.items():
            self.assertGreater(len(steps), 0,
                               f"Playbook '{threat_class}' has no steps")

    def test_playbook_step_has_action_type(self):
        for steps in self.PLAYBOOKS.values():
            for step in steps:
                self.assertTrue(hasattr(step, "action_type"),
                                "PlaybookStep must have action_type")

    def test_playbook_step_has_description(self):
        for steps in self.PLAYBOOKS.values():
            for step in steps:
                self.assertTrue(hasattr(step, "description"),
                                "PlaybookStep must have description")

    def test_action_type_is_non_empty_string(self):
        for steps in self.PLAYBOOKS.values():
            for step in steps:
                self.assertIsInstance(step.action_type, str)
                self.assertTrue(len(step.action_type) > 0)


class TestWaterHammerPlaybook(unittest.TestCase):
    """water_hammer: close_valve -> wait -> verify_pressure."""

    def setUp(self):
        from layers.playbooks import PLAYBOOKS
        self.steps = PLAYBOOKS["water_hammer"]

    def test_has_close_valve_step(self):
        action_types = [s.action_type for s in self.steps]
        self.assertIn("close_valve", action_types)

    def test_has_verify_step(self):
        action_types = [s.action_type for s in self.steps]
        has_verify = any("verify" in at for at in action_types)
        self.assertTrue(has_verify, "water_hammer should include a verify step")

    def test_close_valve_is_first(self):
        self.assertEqual(self.steps[0].action_type, "close_valve",
                         "First step of water_hammer must be close_valve")


class TestLoadRedistributionPlaybook(unittest.TestCase):
    """load_redistribution: shed_load -> rebalance."""

    def setUp(self):
        from layers.playbooks import PLAYBOOKS
        self.steps = PLAYBOOKS["load_redistribution"]

    def test_has_shed_load_step(self):
        action_types = [s.action_type for s in self.steps]
        self.assertIn("shed_load", action_types)

    def test_has_rebalance_step(self):
        action_types = [s.action_type for s in self.steps]
        self.assertIn("rebalance", action_types)

    def test_shed_load_before_rebalance(self):
        action_types = [s.action_type for s in self.steps]
        idx_shed = action_types.index("shed_load")
        idx_rebal = action_types.index("rebalance")
        self.assertLess(idx_shed, idx_rebal,
                        "shed_load must precede rebalance in load_redistribution playbook")


class TestScadaReplayPlaybook(unittest.TestCase):
    """scada_replay: force_reread -> diff_check."""

    def setUp(self):
        from layers.playbooks import PLAYBOOKS
        self.steps = PLAYBOOKS["scada_replay"]

    def test_has_force_reread_step(self):
        action_types = [s.action_type for s in self.steps]
        self.assertIn("force_reread", action_types)

    def test_has_diff_check_step(self):
        action_types = [s.action_type for s in self.steps]
        self.assertIn("diff_check", action_types)

    def test_force_reread_before_diff_check(self):
        action_types = [s.action_type for s in self.steps]
        idx_read = action_types.index("force_reread")
        idx_diff = action_types.index("diff_check")
        self.assertLess(idx_read, idx_diff,
                        "force_reread must precede diff_check in scada_replay playbook")


class TestGetPlaybook(unittest.TestCase):
    """get_playbook helper function."""

    def setUp(self):
        from layers.playbooks import get_playbook
        self.get_playbook = get_playbook

    def test_get_playbook_returns_steps_for_known_class(self):
        steps = self.get_playbook("water_hammer")
        self.assertIsNotNone(steps)
        self.assertGreater(len(steps), 0)

    def test_get_playbook_returns_none_for_unknown_class(self):
        result = self.get_playbook("nonexistent_attack_type")
        self.assertIsNone(result)

    def test_get_playbook_case_insensitive(self):
        steps_lower = self.get_playbook("water_hammer")
        steps_upper = self.get_playbook("WATER_HAMMER")
        self.assertIsNotNone(steps_upper,
                             "get_playbook should be case-insensitive")
        self.assertEqual(len(steps_lower), len(steps_upper))


class TestExecutePlaybook(unittest.TestCase):
    """execute_playbook runs steps and returns a result summary."""

    def setUp(self):
        from layers.playbooks import execute_playbook
        self.execute_playbook = execute_playbook

    def _make_twin(self):
        twin = MagicMock()
        twin.state = {"valve_1": {"subsystem": "water"}}
        return twin

    def test_execute_returns_dict(self):
        twin = self._make_twin()
        result = self.execute_playbook("water_hammer", "valve_1", twin)
        self.assertIsInstance(result, dict)

    def test_execute_result_has_threat_class(self):
        twin = self._make_twin()
        result = self.execute_playbook("water_hammer", "valve_1", twin)
        self.assertIn("threat_class", result)
        self.assertEqual(result["threat_class"], "water_hammer")

    def test_execute_result_has_steps_executed(self):
        twin = self._make_twin()
        result = self.execute_playbook("water_hammer", "valve_1", twin)
        self.assertIn("steps_executed", result)
        self.assertGreater(result["steps_executed"], 0)

    def test_execute_unknown_class_returns_none(self):
        twin = self._make_twin()
        result = self.execute_playbook("totally_unknown", "valve_1", twin)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
