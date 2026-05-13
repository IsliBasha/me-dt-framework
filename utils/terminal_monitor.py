"""Rich terminal companion — displays live simulation status."""

from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

_console = Console() if _RICH_OK else None

_SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH":     "red",
    "MEDIUM":   "yellow",
    "LOW":      "cyan",
    "NONE":     "green",
}


def print_tick_summary(
    tick: int,
    threat_level: str,
    violations: List[Dict],
    mode_a: Optional[Any],
    cusum_count: int,
    isoforest_hit: bool,
    active_attack: Optional[str],
    speed: float,
):
    if not _RICH_OK or _console is None:
        _plain_summary(tick, threat_level, violations, mode_a, active_attack)
        return

    color = _SEVERITY_COLORS.get(threat_level, "white")
    parts = [
        f"[bold]Tick {tick:4d}[/bold]",
        f"[{color}]Threat: {threat_level:<8}[/{color}]",
        f"Speed: {speed:.1f}x",
        f"Violations: {len(violations):2d}",
        f"CUSUM: {cusum_count:2d}",
        f"IF: {'HIT' if isoforest_hit else '---'}",
    ]
    if active_attack:
        parts.append(f"[bold red]ATTACK: {active_attack}[/bold red]")
    if mode_a:
        tc = mode_a.threat_class
        cf = mode_a.confidence
        parts.append(f"AI: [{cf:.0%}] {tc}")

    _console.print("  ".join(parts))


def _plain_summary(tick, threat_level, violations, mode_a, active_attack):
    attack_str = f" | ATTACK: {active_attack}" if active_attack else ""
    ai_str = f" | AI: {mode_a.threat_class}({mode_a.confidence:.0%})" if mode_a else ""
    print(f"[T{tick:4d}] {threat_level:<8} | violations={len(violations)}{attack_str}{ai_str}")
