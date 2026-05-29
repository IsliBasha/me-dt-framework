"""
Audit log — appends Mythos AI transcripts to a per-run JSONL file.
"""

import json
import os
from datetime import datetime, timezone

_run_id: str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def get_run_id() -> str:
    return _run_id


def append_transcript(record: dict) -> None:
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", f"transcripts_{_run_id}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
