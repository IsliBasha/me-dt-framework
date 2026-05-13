"""
Ticket #3: Mode C fires constantly in demo mode (no API key).
Root cause: gate only checks confidence < 0.40, but mock always returns 0.10.
Fix: add api_key guard — extract _should_fire_mode_c(mode_a_result, violations, api_key).
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _should_fire_mode_c
from models.state_vector import ThreatAssessment


def _assessment(confidence: float) -> ThreatAssessment:
    return ThreatAssessment(
        threat_class="NONE",
        confidence=confidence,
        evidence_trace="",
        affected_subsystems=[],
        physical_consequence="",
        recommended_response="",
        reasoning_chain="",
        tick=0,
        api_latency_ms=0.0,
    )


_VIOLATIONS = [{"rule_id": "W2", "severity": "MEDIUM"}]


class TestModeCGate(unittest.TestCase):

    # --- demo mode (no API key) ---

    def test_suppressed_in_demo_mode_even_with_low_confidence(self):
        """Mode C must NOT fire in demo mode even though mock confidence is 0.10."""
        result = _should_fire_mode_c(_assessment(0.10), _VIOLATIONS, api_key="")
        self.assertFalse(result,
            "Mode C fired in demo mode — will spam zero-day hypotheses every tick")

    def test_suppressed_in_demo_mode_with_many_violations(self):
        """Multiple violations must not override the API key guard in demo mode."""
        many = _VIOLATIONS * 5
        result = _should_fire_mode_c(_assessment(0.10), many, api_key="")
        self.assertFalse(result)

    # --- live mode (API key present) ---

    def test_fires_with_api_key_low_confidence_and_violations(self):
        """Mode C must fire when key is set, confidence < 0.40, and violations exist."""
        result = _should_fire_mode_c(_assessment(0.30), _VIOLATIONS, api_key="sk-ant-test")
        self.assertTrue(result)

    def test_fires_at_confidence_just_below_threshold(self):
        """Confidence of 0.39 with key and violations must trigger Mode C."""
        result = _should_fire_mode_c(_assessment(0.39), _VIOLATIONS, api_key="sk-ant-test")
        self.assertTrue(result)

    # --- suppress on other conditions (with or without key) ---

    def test_suppressed_when_confidence_at_threshold(self):
        """Confidence of exactly 0.40 must NOT trigger Mode C (not strictly below)."""
        result = _should_fire_mode_c(_assessment(0.40), _VIOLATIONS, api_key="sk-ant-test")
        self.assertFalse(result)

    def test_suppressed_when_confidence_above_threshold(self):
        """High-confidence Mode A result (0.85) must not trigger Mode C."""
        result = _should_fire_mode_c(_assessment(0.85), _VIOLATIONS, api_key="sk-ant-test")
        self.assertFalse(result)

    def test_suppressed_when_no_violations(self):
        """No violations means no Mode C, even with key and low confidence."""
        result = _should_fire_mode_c(_assessment(0.10), [], api_key="sk-ant-test")
        self.assertFalse(result)

    def test_suppressed_when_mode_a_is_none(self):
        """None mode_a_result (API timeout etc.) must not trigger Mode C."""
        result = _should_fire_mode_c(None, _VIOLATIONS, api_key="sk-ant-test")
        self.assertFalse(result)

    def test_suppressed_when_both_no_key_and_no_violations(self):
        """Doubly gated: no key AND no violations still stays silent."""
        result = _should_fire_mode_c(_assessment(0.10), [], api_key="")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
