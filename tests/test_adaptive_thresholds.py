"""
Tests for attack-adaptive detector thresholds.
RED: all tests fail until baselines/cusum_detector.py, baselines/isolation_forest.py,
and layers/adaptive_thresholds.py gain the required functions.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCusumPerNodeThreshold(unittest.TestCase):
    """cusum_detector should support per-node h overrides."""

    def setUp(self):
        import baselines.cusum_detector as cusum
        cusum.reset_all()
        self.cusum = cusum

    def tearDown(self):
        self.cusum.reset_all()

    def test_set_node_threshold_function_exists(self):
        self.assertTrue(hasattr(self.cusum, "set_node_threshold"))

    def test_get_node_threshold_function_exists(self):
        self.assertTrue(hasattr(self.cusum, "get_node_threshold"))

    def test_default_threshold_is_config_h(self):
        import config
        result = self.cusum.get_node_threshold("some_node")
        self.assertAlmostEqual(result, config.CUSUM_H)

    def test_set_node_threshold_stores_value(self):
        self.cusum.set_node_threshold("node_a", 2.5)
        self.assertAlmostEqual(self.cusum.get_node_threshold("node_a"), 2.5)

    def test_tightened_threshold_triggers_earlier(self):
        """Node with h=2.0 should alert before a node with default h=5.0."""
        node_tight = "tight_node"
        node_normal = "normal_node"
        self.cusum.set_node_threshold(node_tight, 2.0)

        for i in range(10):
            self.cusum.update(node_tight, 50.0, i)
            self.cusum.update(node_normal, 50.0, i)

        tight_alerted = False
        for tick in range(10, 20):
            r_tight = self.cusum.update(node_tight, 70.0, tick)
            if r_tight:
                tight_alerted = True

        self.assertTrue(tight_alerted, "Tight-threshold node should have alerted")

    def test_set_threshold_reset_all_clears_overrides(self):
        self.cusum.set_node_threshold("node_b", 1.5)
        self.cusum.reset_all()
        import config
        self.assertAlmostEqual(self.cusum.get_node_threshold("node_b"), config.CUSUM_H)


class TestIsoForestAdaptiveContamination(unittest.TestCase):
    """isolation_forest should support runtime contamination override."""

    def setUp(self):
        import baselines.isolation_forest as iso
        iso.reset()
        self.iso = iso

    def tearDown(self):
        self.iso.reset()

    def test_set_contamination_function_exists(self):
        self.assertTrue(hasattr(self.iso, "set_contamination"))

    def test_get_contamination_function_exists(self):
        self.assertTrue(hasattr(self.iso, "get_contamination"))

    def test_default_contamination_is_config_value(self):
        import config
        result = self.iso.get_contamination()
        self.assertAlmostEqual(result, config.ISOFOREST_CONTAMINATION)

    def test_set_contamination_stores_value(self):
        self.iso.set_contamination(0.15)
        self.assertAlmostEqual(self.iso.get_contamination(), 0.15)

    def test_reset_restores_default_contamination(self):
        import config
        self.iso.set_contamination(0.20)
        self.iso.reset()
        self.assertAlmostEqual(self.iso.get_contamination(), config.ISOFOREST_CONTAMINATION)

    def test_contamination_clamped_to_valid_range(self):
        self.iso.set_contamination(0.9)
        result = self.iso.get_contamination()
        self.assertLessEqual(result, 0.5)

    def test_contamination_above_zero(self):
        self.iso.set_contamination(0.0)
        result = self.iso.get_contamination()
        self.assertGreater(result, 0.0)


class TestAdaptiveThresholdsModule(unittest.TestCase):
    """layers/adaptive_thresholds.py orchestrates tightening across detectors."""

    def setUp(self):
        import baselines.cusum_detector as cusum
        import baselines.isolation_forest as iso
        cusum.reset_all()
        iso.reset()

    def tearDown(self):
        import baselines.cusum_detector as cusum
        import baselines.isolation_forest as iso
        cusum.reset_all()
        iso.reset()

    def test_module_importable(self):
        from layers import adaptive_thresholds
        self.assertIsNotNone(adaptive_thresholds)

    def test_tighten_on_confirmed_attack_function_exists(self):
        from layers.adaptive_thresholds import tighten_on_confirmed_attack
        self.assertTrue(callable(tighten_on_confirmed_attack))

    def test_reset_overrides_function_exists(self):
        from layers.adaptive_thresholds import reset_overrides
        self.assertTrue(callable(reset_overrides))

    def test_tighten_sandbox_reduces_cusum_threshold(self):
        import config
        import baselines.cusum_detector as cusum
        from layers.response_tiers import ResponseTier
        from layers.adaptive_thresholds import tighten_on_confirmed_attack

        tighten_on_confirmed_attack(["node_x", "node_y"], ResponseTier.SANDBOX)

        h_x = cusum.get_node_threshold("node_x")
        self.assertLess(h_x, config.CUSUM_H,
                        "SANDBOX tier should tighten CUSUM h below default")

    def test_tighten_quarantine_increases_contamination(self):
        import config
        import baselines.isolation_forest as iso
        from layers.response_tiers import ResponseTier
        from layers.adaptive_thresholds import tighten_on_confirmed_attack

        tighten_on_confirmed_attack(["node_q"], ResponseTier.QUARANTINE)

        contamination = iso.get_contamination()
        self.assertGreater(contamination, config.ISOFOREST_CONTAMINATION,
                           "QUARANTINE tier should raise IsoForest contamination")

    def test_reset_overrides_restores_defaults(self):
        import config
        import baselines.cusum_detector as cusum
        import baselines.isolation_forest as iso
        from layers.response_tiers import ResponseTier
        from layers.adaptive_thresholds import tighten_on_confirmed_attack, reset_overrides

        tighten_on_confirmed_attack(["node_r"], ResponseTier.QUARANTINE)
        reset_overrides()

        self.assertAlmostEqual(cusum.get_node_threshold("node_r"), config.CUSUM_H)
        self.assertAlmostEqual(iso.get_contamination(), config.ISOFOREST_CONTAMINATION)

    def test_monitor_tier_does_not_tighten(self):
        import config
        import baselines.cusum_detector as cusum
        from layers.response_tiers import ResponseTier
        from layers.adaptive_thresholds import tighten_on_confirmed_attack

        tighten_on_confirmed_attack(["node_m"], ResponseTier.MONITOR)

        h = cusum.get_node_threshold("node_m")
        self.assertAlmostEqual(h, config.CUSUM_H,
                               msg="MONITOR tier should not tighten thresholds")


if __name__ == "__main__":
    unittest.main()
