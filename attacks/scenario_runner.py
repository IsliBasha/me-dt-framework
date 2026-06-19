"""
Ticket 1 — Scenario Scripting & Replay Engine
Loads YAML/JSON attack scripts and triggers scenario injection at specified ticks.
"""

import json
import os
from typing import Any, Dict, List

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scenarios", "scripts")


class ScriptValidationError(ValueError):
    pass


def load_script(path: str) -> List[Dict[str, Any]]:
    """Load and validate an attack script from a JSON or YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Script not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    with open(path) as f:
        if ext in (".yaml", ".yml"):
            try:
                import yaml
                entries = yaml.safe_load(f) or []
            except ImportError:
                raise ImportError("PyYAML is required for .yaml scripts: pip install pyyaml")
        else:
            entries = json.load(f)

    if not isinstance(entries, list):
        raise ScriptValidationError("Script must be a JSON/YAML array of steps")

    for i, entry in enumerate(entries):
        if "at_tick" not in entry:
            raise ScriptValidationError(f"Step {i} missing required field 'at_tick'")
        if "scenario" not in entry:
            raise ScriptValidationError(f"Step {i} missing required field 'scenario'")
        if not isinstance(entry["at_tick"], (int, float)) or entry["at_tick"] < 0:
            raise ScriptValidationError(
                f"Step {i} 'at_tick' must be a non-negative number, got {entry['at_tick']!r}"
            )

    return entries


def list_scripts() -> List[Dict[str, Any]]:
    """Return metadata for all scripts found in SCRIPTS_DIR."""
    scripts_dir = SCRIPTS_DIR
    if not os.path.isdir(scripts_dir):
        return []

    result = []
    for fname in sorted(os.listdir(scripts_dir)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in (".json", ".yaml", ".yml"):
            continue
        name = os.path.splitext(fname)[0]
        fpath = os.path.join(scripts_dir, fname)
        try:
            entries = load_script(fpath)
            steps = len(entries)
        except Exception:
            steps = 0
        result.append({"name": name, "file": fname, "steps": steps})
    return result


def get_due_steps(script: List[Dict[str, Any]], tick: int) -> List[Dict[str, Any]]:
    """Return steps whose at_tick matches the current tick."""
    return [s for s in script if int(s["at_tick"]) == tick]
