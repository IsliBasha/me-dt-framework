"""
Ticket 7 — Persistent Vulnerability Atlas
Stores, deduplicates, ranks, and persists Mode B attack paths across runs.
Dedup key: (entry_point, attack_steps[0].action)
Rank:      severity × (1 - detection_difficulty_score)
"""

import json
import os
from typing import Any, Dict, List, Optional

_DIFFICULTY_SCORES = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8}
_DEFAULT_PERSIST = os.path.join(os.path.dirname(__file__), "..", "reports", "atlas.jsonl")


def _dedup_key(entry: Dict[str, Any]) -> str:
    ep    = entry.get("entry_point", "")
    steps = entry.get("attack_steps") or []
    first_action = steps[0].get("action", "") if steps else ""
    return f"{ep}||{first_action}"


def _score(entry: Dict[str, Any]) -> float:
    severity   = float(entry.get("estimated_impact_severity", 5))
    difficulty = entry.get("detection_difficulty", "MEDIUM")
    diff_score = _DIFFICULTY_SCORES.get(difficulty, 0.5)
    return severity * (1.0 - diff_score)


class VulnerabilityAtlas:
    def __init__(self, persist_path: Optional[str] = None):
        self._persist_path = persist_path or _DEFAULT_PERSIST
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._persist_path):
            return
        with open(self._persist_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    key = _dedup_key(entry)
                    self._entries[key] = entry
                except (json.JSONDecodeError, KeyError):
                    pass

    def _append_to_disk(self, entry: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._persist_path)), exist_ok=True)
        with open(self._persist_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def add(self, entry: Dict[str, Any]) -> None:
        key = _dedup_key(entry)
        if key not in self._entries:
            self._entries[key] = entry
            self._append_to_disk(entry)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._entries.values())

    def ranked(self) -> List[Dict[str, Any]]:
        entries = [dict(e, score=round(_score(e), 3)) for e in self._entries.values()]
        return sorted(entries, key=lambda e: e["score"], reverse=True)

    def __len__(self) -> int:
        return len(self._entries)
