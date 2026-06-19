"""
Comparison metrics collector for TP/FP/latency + TTD comparison table.
Records injection tick and detection tick per attack per detector.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from models.attack_scenarios import SCENARIO_DEFINITIONS

_DETECTORS = ["ME-DT", "CUSUM", "ISOFOREST"]

# Per-attack, per-detector tracking
_injection_ticks: Dict[str, int] = {}
_detection_ticks: Dict[str, Dict[str, Optional[int]]] = {}
_fp_counts:       Dict[str, int] = {"ME-DT": 0, "CUSUM": 0, "ISOFOREST": 0}
_tp_counts:       Dict[str, int] = {"ME-DT": 0, "CUSUM": 0, "ISOFOREST": 0}
_latencies_ms:    List[float]    = []
_clean_period_end: int = 20
_alerts_by_class: Dict[str, int] = {}

# Token & cost tracking (Ticket 4)
_total_input_tokens:  int   = 0
_total_output_tokens: int   = 0
_total_cost_usd:      float = 0.0
_tokens_by_mode: Dict[str, Dict[str, int]] = {}


def record_injection(scenario: str, tick: int):
    _injection_ticks[scenario] = tick
    _detection_ticks.setdefault(scenario, {"ME-DT": None, "CUSUM": None, "ISOFOREST": None})


def record_detection(detector: str, scenario_hint: Optional[str], tick: int):
    """Record that a detector fired at this tick."""
    # Credit to active scenario if within window
    for scenario, inj_tick in _injection_ticks.items():
        det = _detection_ticks.get(scenario, {})
        if det.get(detector) is None and abs(tick - inj_tick) <= 15:
            det[detector] = tick
            _detection_ticks[scenario] = det
            _tp_counts[detector] = _tp_counts.get(detector, 0) + 1
            return
    # No active scenario — count as false positive if in clean period
    if tick <= _clean_period_end:
        _fp_counts[detector] = _fp_counts.get(detector, 0) + 1


def record_latency(latency_ms: float):
    _latencies_ms.append(latency_ms)


def record_token_usage(mode: str, *, in_tokens: int, out_tokens: int) -> None:
    global _total_input_tokens, _total_output_tokens, _total_cost_usd
    _total_input_tokens  += in_tokens
    _total_output_tokens += out_tokens
    _total_cost_usd += (
        in_tokens  * config.ANTHROPIC_PRICE_PER_MTOK_INPUT  / 1_000_000
        + out_tokens * config.ANTHROPIC_PRICE_PER_MTOK_OUTPUT / 1_000_000
    )
    bucket = _tokens_by_mode.setdefault(mode, {"input_tokens": 0, "output_tokens": 0})
    bucket["input_tokens"]  += in_tokens
    bucket["output_tokens"] += out_tokens


def record_class_alert(threat_class: str):
    _alerts_by_class[threat_class] = _alerts_by_class.get(threat_class, 0) + 1


def set_clean_period_end(tick: int) -> None:
    global _clean_period_end
    _clean_period_end = tick


def get_summary() -> Dict[str, Any]:
    mean_lat = sum(_latencies_ms) / len(_latencies_ms) if _latencies_ms else 0.0
    total_me = sum(_tp_counts.get("ME-DT", 0) for _ in [1])
    total_fp = _fp_counts.get("ME-DT", 0)

    rows = []
    for scenario in SCENARIO_DEFINITIONS:
        det = _detection_ticks.get(scenario, {})
        inj = _injection_ticks.get(scenario)
        row = {"scenario": scenario}
        for d in _DETECTORS:
            det_tick = det.get(d)
            if inj is not None and det_tick is not None:
                row[f"{d}_ttd"] = det_tick - inj
            else:
                row[f"{d}_ttd"] = None
        rows.append(row)

    # Per-detector confusion matrix (Ticket 8)
    # TN = clean_period_end - FP (clean ticks where no alert fired)
    # FN = injections where detector never fired within window
    cm: Dict[str, Dict[str, int]] = {}
    for det in _DETECTORS:
        tp = _tp_counts.get(det, 0)
        fp = _fp_counts.get(det, 0)
        tn = max(0, _clean_period_end - fp)
        fn = sum(
            1 for det_map in _detection_ticks.values()
            if det_map.get(det) is None
        )
        cm[det] = {"TP": tp, "FP": fp, "TN": tn, "FN": fn}

    return {
        "token_usage": {
            "total_input_tokens":  _total_input_tokens,
            "total_output_tokens": _total_output_tokens,
            "total_cost_usd":      round(_total_cost_usd, 6),
            "by_mode":             {m: dict(v) for m, v in _tokens_by_mode.items()},
        },
        "confusion_matrix": cm,
        "comparison_table": rows,
        "me_dt": {
            "tp_count":       _tp_counts.get("ME-DT", 0),
            "fp_count":       _fp_counts.get("ME-DT", 0),
            "mean_latency_ms": round(mean_lat, 1),
            "alerts_by_class": _alerts_by_class,
        },
        "cusum": {
            "alerts_count": sum(
                1 for d in _detection_ticks.values() if d.get("CUSUM") is not None
            ) + _fp_counts.get("CUSUM", 0),
            "fp_count": _fp_counts.get("CUSUM", 0),
        },
        "isoforest": {
            "alerts_count": sum(
                1 for d in _detection_ticks.values() if d.get("ISOFOREST") is not None
            ) + _fp_counts.get("ISOFOREST", 0),
            "fp_count": _fp_counts.get("ISOFOREST", 0),
        },
    }


def export_report(tick: int):
    os.makedirs("reports", exist_ok=True)
    summary = get_summary()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON report
    with open(f"reports/metrics_{ts}.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Markdown report
    with open(f"reports/comparison_{ts}.md", "w") as f:
        f.write(f"# ME-DT Comparison Report\n\nGenerated at tick {tick}  |  {ts}\n\n")
        f.write("## Detection Time Comparison (ticks to first alert)\n\n")
        f.write("| Attack | CUSUM TTD | IsoForest TTD | ME-DT TTD |\n")
        f.write("|--------|-----------|---------------|----------|\n")
        for row in summary["comparison_table"]:
            c = row.get("CUSUM_ttd", "—")
            i = row.get("ISOFOREST_ttd", "—")
            m = row.get("ME-DT_ttd", "—")
            f.write(f"| {row['scenario']:<30} | {str(c):>9} | {str(i):>13} | {str(m):>9} |\n")
        f.write(f"\n## ME-DT Metrics\n\n")
        f.write(f"- Mean API latency: {summary['me_dt']['mean_latency_ms']} ms\n")
        f.write(f"- True positives: {summary['me_dt']['tp_count']}\n")
        f.write(f"- False positives (clean period): {summary['me_dt']['fp_count']}\n\n")

    print(f"[Metrics] Reports exported to reports/")
    return summary


def reset():
    global _total_input_tokens, _total_output_tokens, _total_cost_usd, _clean_period_end
    _injection_ticks.clear()
    _detection_ticks.clear()
    _fp_counts.update({"ME-DT": 0, "CUSUM": 0, "ISOFOREST": 0})
    _tp_counts.update({"ME-DT": 0, "CUSUM": 0, "ISOFOREST": 0})
    _latencies_ms.clear()
    _alerts_by_class.clear()
    _total_input_tokens  = 0
    _total_output_tokens = 0
    _total_cost_usd      = 0.0
    _tokens_by_mode.clear()
    _clean_period_end    = 20
