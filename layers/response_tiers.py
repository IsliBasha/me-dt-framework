"""
Response tier classification: maps confidence scores to action tiers.

NONE      confidence < 0.50   — below detection threshold
MONITOR   0.50 <= conf < 0.75 — log only, no action
SANDBOX   0.75 <= conf < 0.92 — queue for human approval
QUARANTINE conf >= 0.92       — auto-act without human review
"""

from enum import Enum
import config

MONITOR_THRESHOLD = 0.50


class ResponseTier(Enum):
    NONE = "NONE"
    MONITOR = "MONITOR"
    SANDBOX = "SANDBOX"
    QUARANTINE = "QUARANTINE"


def classify_tier(confidence: float) -> ResponseTier:
    if confidence >= config.AUTO_CONTAIN_THRESHOLD:
        return ResponseTier.QUARANTINE
    if confidence >= config.ALERT_THRESHOLD:
        return ResponseTier.SANDBOX
    if confidence >= MONITOR_THRESHOLD:
        return ResponseTier.MONITOR
    return ResponseTier.NONE
