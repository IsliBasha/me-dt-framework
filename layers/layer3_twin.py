"""
Layer 3 — Digital Twin Core
Maintains live state, rolling history, physics validation rules,
causal dependency graph, quarantine, sandboxed clone.
"""

import copy
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
from models.state_vector import NodeReading, PhysicsViolationEvent


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Causal dependency adjacency — which nodes affect which
CAUSAL_GRAPH: Dict[str, List[str]] = {
    # Water: pump -> downstream junctions
    "pump_10":  ["10", "15", "20"],
    "pump_335": ["35", "40", "50"],
    # Power: upstream bus -> downstream buses (radial feeder)
    "0":  ["4", "8", "12", "18", "32"],
    "4":  ["8", "12"],
    "8":  ["12"],
    "18": ["32"],
    # Cross-domain
    "SYN-T01": ["0", "4"],
}


class DigitalTwin:
    def __init__(self):
        self.tick: int = 0
        # node_id -> latest NodeReading dict
        self.state: Dict[str, Dict] = {}
        # node_id -> status override
        self.node_status: Dict[str, str] = {}
        # rolling history: node_id -> deque of (tick, value)
        self.history: Dict[str, deque] = {}
        # active physics violations this tick
        self.active_violations: List[PhysicsViolationEvent] = []
        # quarantine log
        self.quarantine_log: List[Dict] = []
        # previous pump states for cycling detection
        self._prev_pump_status: Dict[str, str] = {}
        # previous vm_pu for cascade detection
        self._prev_vm: Dict[str, float] = {}
        # SIGNAL_ANOMALY active flag for cross-domain rule
        self._signal_anomaly_tick: Optional[int] = None
        # power demand baseline for cross-domain
        self._power_demand_history: deque = deque(maxlen=10)

    def _history_for(self, node_id: str) -> deque:
        if node_id not in self.history:
            self.history[node_id] = deque(maxlen=config.STATE_HISTORY_WINDOW)
        return self.history[node_id]

    def _rolling_mean(self, node_id: str, n: int = 20) -> Optional[float]:
        hist = self._history_for(node_id)
        vals = [v for _, v in hist][-n:]
        return sum(vals) / len(vals) if vals else None

    def _rolling_std(self, node_id: str, n: int = 30) -> Optional[float]:
        hist = self._history_for(node_id)
        vals = [v for _, v in hist][-n:]
        if len(vals) < 2:
            return None
        mean = sum(vals) / len(vals)
        return (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5

    def update(self, clean_stream: List[NodeReading], tick: int):
        self.tick = tick
        self.active_violations = []

        # Update state
        for reading in clean_stream:
            nid = reading.node_id
            status = self.node_status.get(nid, reading.status)
            self.state[nid] = {
                "node_id":      nid,
                "subsystem":    reading.subsystem,
                "metric":       reading.metric,
                "value":        reading.value,
                "unit":         reading.unit,
                "source":       reading.source,
                "protocol":     reading.protocol,
                "status":       status,
                "timestamp_iso": reading.timestamp_iso,
            }
            self._history_for(nid).append((tick, reading.value))

        self._run_physics_rules(tick)

    # ------------------------------------------------------------------
    # Physics validation
    # ------------------------------------------------------------------

    def _violation(
        self,
        rule_id: str,
        description: str,
        affected: List[str],
        subsystem: str,
        severity: str,
        tick: int,
        cross_domain: bool = False,
        traffic_model: Optional[str] = None,
    ) -> PhysicsViolationEvent:
        ev = PhysicsViolationEvent(
            rule_id=rule_id,
            description=description,
            affected_nodes=affected,
            subsystem=subsystem,
            severity=severity,
            tick=tick,
            timestamp_iso=_iso_now(),
            cross_domain=cross_domain,
            traffic_model=traffic_model,
        )
        self.active_violations.append(ev)
        return ev

    def _run_physics_rules(self, tick: int):
        water_nodes = {k: v for k, v in self.state.items() if v.get("subsystem") == "water"}
        power_nodes = {k: v for k, v in self.state.items() if v.get("subsystem") == "power"}
        traffic_nodes = {k: v for k, v in self.state.items() if v.get("subsystem") == "traffic"}

        # ---- WATER rules ----
        pump_toggles = []
        for nid, nd in water_nodes.items():
            if not nid.startswith("pump_"):
                continue
            curr = str(nd.get("status", ""))
            prev = self._prev_pump_status.get(nid, curr)
            if curr != prev:
                pump_toggles.append(nid)
            self._prev_pump_status[nid] = curr

        # W1: pump-induced pressure transient on downstream junctions
        _PUMP_DOWNSTREAM: Dict[str, List[str]] = {
            "pump_10":  ["10", "15", "20"],
            "pump_335": ["35", "40", "50"],
        }
        w1_nodes: List[str] = []
        for downstream in _PUMP_DOWNSTREAM.values():
            for nid in downstream:
                if nid not in water_nodes:
                    continue
                hist = [(t, v) for t, v in self._history_for(nid)
                        if t >= tick - config.PUMP_PRESSURE_CHECK_WINDOW]
                if len(hist) >= 2:
                    delta = abs(hist[-1][1] - hist[0][1])
                    if delta > config.PUMP_PRESSURE_DELTA_THRESHOLD:
                        w1_nodes.append(nid)
        if w1_nodes:
            self._violation(
                "W1",
                f"Pump-induced pressure transient on {len(w1_nodes)} downstream junction(s)",
                w1_nodes, "water", "HIGH", tick,
            )

        # W3: rapid pump cycling
        if len(pump_toggles) >= 2:
            self._violation(
                "W3", "Rapid pump cycling — water hammer indicator",
                pump_toggles, "water", "HIGH", tick,
            )

        # W2: pressure underflow — adaptive per-node baseline (not fixed threshold)
        # Baseline excludes the current reading (hist[-(W+1):-1]) so the anomaly
        # being evaluated is never part of its own reference distribution.
        # Secondary ramp check catches low-and-slow attacks that evade sigma.
        low_pressure = []
        for nid, nd in water_nodes.items():
            if nid.startswith("pump_"):
                continue
            p = nd.get("value", 100.0)
            if not isinstance(p, (int, float)):
                continue
            hist_vals = [v for _, v in self._history_for(nid)]
            # Need WARMUP_TICKS+1: one extra so baseline excludes the current reading
            if len(hist_vals) < config.W2_WARMUP_TICKS + 1:
                continue
            baseline = hist_vals[-(config.W2_BASELINE_WINDOW + 1):-1]
            mean = sum(baseline) / len(baseline)
            variance = sum((v - mean) ** 2 for v in baseline) / len(baseline)
            std = variance ** 0.5
            flagged = False
            if std < 0.5:
                if mean - p >= config.W2_MIN_DROP_M:
                    flagged = True
            else:
                if p < mean - config.W2_SIGMA_THRESHOLD * std:
                    flagged = True
            # Secondary: oldest value in window vs current — catches ramp attacks
            if not flagged and baseline[0] - p >= config.W2_MIN_DROP_M:
                flagged = True
            if flagged:
                low_pressure.append(nid)
        if low_pressure:
            self._violation(
                "W2", "Pressure underflow: drop below per-node rolling baseline",
                low_pressure, "water", "MEDIUM", tick,
            )

        # W4: flow surge (using rolling mean of pressure as proxy)
        flow_surge = []
        for nid, nd in water_nodes.items():
            if nid.startswith("pump_"):
                continue
            mean = self._rolling_mean(nid, 20)
            val  = nd.get("value", 0.0)
            if mean and mean > 0 and isinstance(val, (int, float)) and val > 2 * mean:
                flow_surge.append(nid)
        if flow_surge:
            self._violation("W4", "Flow surge (>2x rolling mean)", flow_surge, "water", "MEDIUM", tick)

        # ---- POWER rules ----
        cascade_candidates = []
        for nid, nd in power_nodes.items():
            vm = nd.get("value") if nd.get("metric") == "vm_pu" else nd.get("vm_pu") or nd.get("value")
            if not isinstance(vm, (int, float)):
                # try vm_pu key directly
                vm = nd.get("vm_pu")
            if not isinstance(vm, (int, float)):
                continue

            # P1: voltage violation
            if vm < 0.90 or vm > 1.10:
                self._violation(
                    "P1", f"Voltage violation: {vm:.3f} pu (IEEE 0.90-1.10 band)",
                    [nid], "power", "HIGH", tick,
                )

            # P4: cascade risk — check vm drop vs previous tick
            prev_vm = self._prev_vm.get(nid)
            if prev_vm is not None and abs(vm - prev_vm) > 0.05:
                cascade_candidates.append(nid)
            self._prev_vm[nid] = vm

        if len(cascade_candidates) >= 3:
            self._violation("P4", "Cascade risk: 3+ buses with >0.05 pu drop in one tick",
                            cascade_candidates, "power", "HIGH", tick)

        # P2: line overload — check loading_pct field
        for nid, nd in power_nodes.items():
            lp = nd.get("loading_pct", 0.0)
            if isinstance(lp, (int, float)) and lp > 100:
                self._violation("P2", f"Line overload {lp:.1f}%", [nid], "power", "CRITICAL", tick)

        # P3: grid collapse sentinel
        if self.state.get("__grid_collapse__"):
            self._violation("P3", "Load flow did not converge — GRID COLLAPSE",
                            list(power_nodes.keys())[:5], "power", "CRITICAL", tick)

        # ---- TRAFFIC rules ----
        green_count = sum(
            1 for nd in traffic_nodes.values()
            if nd.get("signal_phase") == "GREEN"
        )
        zero_flow = [
            nid for nid, nd in traffic_nodes.items()
            if isinstance(nd.get("value") or nd.get("vehicle_flow"), (int, float))
            and (nd.get("value") or nd.get("vehicle_flow") or 0) == 0
        ]

        signal_anomaly_active = False
        if green_count >= 4:
            self._violation(
                "T1", f"Signal anomaly: {green_count} simultaneous GREEN signals",
                [nid for nid, nd in traffic_nodes.items() if nd.get("signal_phase") == "GREEN"],
                "traffic", "MEDIUM", tick,
                traffic_model="SYNTHETIC - treat as illustrative only",
            )
            signal_anomaly_active = True
            self._signal_anomaly_tick = tick

        if len(zero_flow) >= 3:
            self._violation(
                "T2", "Traffic blackout: 3+ nodes with zero vehicle flow",
                zero_flow, "traffic", "LOW", tick,
                traffic_model="SYNTHETIC - treat as illustrative only",
            )

        # ---- CROSS-DOMAIN rules ----
        # X1: SIGNAL_ANOMALY + power demand rise > 15% within 5 ticks
        if self._signal_anomaly_tick and tick - self._signal_anomaly_tick <= 5:
            total_p = sum(
                nd.get("value") or 0 for nd in power_nodes.values()
                if isinstance(nd.get("value"), (int, float))
            )
            self._power_demand_history.append(total_p)
            if len(self._power_demand_history) >= 2:
                baseline = list(self._power_demand_history)[0]
                if baseline != 0 and (total_p - baseline) / abs(baseline) > 0.15:
                    self._violation(
                        "X1", "Cross-domain correlation: signal anomaly + power demand spike",
                        [], "cross_domain", "HIGH", tick, cross_domain=True,
                    )

        # X2: water pressure underflow on 3+ nodes AND power voltage violation simultaneously
        puf_nodes = [ev for ev in self.active_violations if ev.rule_id == "W2"]
        pv_nodes  = [ev for ev in self.active_violations if ev.rule_id == "P1"]
        if puf_nodes and len(puf_nodes[0].affected_nodes) >= 3 and pv_nodes:
            self._violation(
                "X2", "Infrastructure stress: simultaneous water pressure underflow + power voltage violation",
                puf_nodes[0].affected_nodes + pv_nodes[0].affected_nodes,
                "cross_domain", "CRITICAL", tick, cross_domain=True,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state_snapshot(self) -> Dict:
        water   = {k: v for k, v in self.state.items() if v.get("subsystem") == "water" and not k.startswith("__")}
        power   = {k: v for k, v in self.state.items() if v.get("subsystem") == "power" and not k.startswith("__")}
        traffic = {k: v for k, v in self.state.items() if v.get("subsystem") == "traffic"}
        return {
            "tick":       self.tick,
            "water":      water,
            "power":      power,
            "traffic":    traffic,
            "violations": [
                {
                    "rule_id":       v.rule_id,
                    "description":   v.description,
                    "affected_nodes": v.affected_nodes,
                    "subsystem":     v.subsystem,
                    "severity":      v.severity,
                    "tick":          v.tick,
                    "timestamp_iso": v.timestamp_iso,
                    "cross_domain":  v.cross_domain,
                    "traffic_model": v.traffic_model,
                }
                for v in self.active_violations
            ],
            "node_statuses": dict(self.node_status),
        }

    def get_sandboxed_clone(self) -> Dict:
        """Deep copy of state — no references to live simulator objects."""
        return copy.deepcopy(self.get_state_snapshot())

    def quarantine_node(self, node_id: str, wn=None, net=None):
        self.node_status[node_id] = "QUARANTINED"
        self.quarantine_log.append({
            "node_id":      node_id,
            "tick":         self.tick,
            "timestamp_iso": _iso_now(),
        })
        # Propagate to simulator if possible
        if wn is not None:
            try:
                import wntr
                node = wn.get_node(node_id)
                if node is not None:
                    for link_id, link in wn.links():
                        if (hasattr(link, "start_node_name") and
                                link.start_node_name == node_id or
                                (hasattr(link, "end_node_name") and
                                 link.end_node_name == node_id)):
                            link.initial_status = wntr.network.LinkStatus.Closed
            except Exception:
                pass
        if net is not None:
            try:
                bus_id = int(node_id)
                net.bus.at[bus_id, "in_service"] = False
            except Exception:
                pass

    def set_node_attack(self, node_id: str):
        self.node_status[node_id] = "UNDER_ATTACK"

    def clear_node_status(self, node_id: str):
        self.node_status.pop(node_id, None)
