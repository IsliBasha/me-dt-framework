"""
Attack Scenario Library — 8 physically valid scenarios.
All attacks mutate WNTR wn or pandapower net objects directly.
Telemetry is never mutated — the physical simulators produce anomalous
output naturally from the manipulated model.
"""

import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

import config

# City-map visible node sets (must match city_map.js WATER/POWER/TRAFFIC_NODES)
_VISIBLE_POWER_INTS = [0, 4, 8, 12, 18, 32]
_ALL_WATER_NODES    = ['10','15','20','35','40','50','115','117']
_ALL_POWER_NODES    = ['0','4','8','12','18','32']
_ALL_TRAFFIC_NODES  = ['SYN-T01','SYN-T02','SYN-T03','SYN-T04','SYN-T05','SYN-T06']
_ALL_WATER_SET      = set(_ALL_WATER_NODES)


def _nearest_visible_power(bus_id: int) -> str:
    return str(min(_VISIBLE_POWER_INTS, key=lambda x: abs(x - bus_id)))


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

_active: Dict[str, Dict] = {}          # scenario_name -> {start_tick, ...}
_scada_snapshot: Optional[Dict] = None # for scada_replay


def is_active(name: str, tick: int) -> bool:
    entry = _active.get(name)
    if not entry:
        return False
    elapsed = tick - entry["start_tick"]
    duration = entry.get("duration", config.ATTACK_DURATION_TICKS)
    return elapsed < duration


def get_active_attacks(tick: int) -> Dict[str, bool]:
    return {name: is_active(name, tick) for name in _active}


def inject(name: str, tick: int, delay: int = 0, duration: Optional[int] = None):
    """Schedule an attack to start at tick + delay."""
    start = tick + delay
    _active[name] = {
        "start_tick": start,
        "duration":   duration or config.ATTACK_DURATION_TICKS,
    }
    print(f"[Attacks] Scheduled '{name}' to start at tick {start}")


def clear_attack(name: str):
    _active.pop(name, None)


def reset_all():
    _active.clear()


# ---------------------------------------------------------------------------
# Attack application — called every tick by main simulation loop
# ---------------------------------------------------------------------------

def apply_attacks(tick: int, wn, net, attack_state: Dict) -> Dict[str, bool]:
    """
    Apply all currently active attacks to wn/net.
    Returns dict: attack_name -> is_currently_active
    """
    result: Dict[str, bool] = {}

    for name in list(_active.keys()):
        if not is_active(name, tick):
            result[name] = False
            continue
        result[name] = True

        if name == "false_data_injection":
            _apply_fdi_water(tick, wn)
        elif name == "water_hammer":
            _apply_water_hammer(tick, wn)
        elif name == "load_redistribution":
            _apply_load_redistribution(tick, net)
        elif name == "false_data_injection_power":
            _apply_fdi_power(tick, net)
        elif name == "scada_replay":
            _apply_scada_replay(tick, net)
        elif name == "cross_domain_cascade":
            _apply_cross_domain_cascade(tick, net, attack_state)
        elif name == "actuator_hijack":
            _apply_actuator_hijack(tick, wn)
        elif name == "low_and_slow_recon":
            _apply_low_slow_recon(tick, wn, net)
        elif name == "denial_of_service_ot":
            # DoS is implemented in Layer 2 (packet drop)
            attack_state["denial_of_service_ot"] = {"active": True}

    # Clear DoS if no longer active
    if "denial_of_service_ot" not in result or not result.get("denial_of_service_ot"):
        attack_state.pop("denial_of_service_ot", None)

    return result


# ---------------------------------------------------------------------------
# Individual attack implementations
# ---------------------------------------------------------------------------

def _apply_fdi_water(tick: int, wn):
    if wn is None:
        return
    # Zero demand on 3 junctions
    targets = ["10", "15", "20"]
    for nid in targets:
        try:
            node = wn.get_node(nid)
            if node and hasattr(node, "demand_timeseries_list"):
                for ts in node.demand_timeseries_list:
                    ts.base_value = 0.0
        except Exception:
            pass


def _apply_water_hammer(tick: int, wn):
    if wn is None:
        return
    import wntr
    targets = list(wn.pump_name_list)[:2]
    for pump_id in targets:
        try:
            pump = wn.get_link(pump_id)
            if pump is None:
                continue
            if tick % 2 == 0:
                pump.initial_status = wntr.network.LinkStatus.Open
            else:
                pump.initial_status = wntr.network.LinkStatus.Closed
        except Exception:
            pass


def _apply_load_redistribution(tick: int, net):
    if net is None:
        return
    try:
        import pandapower as pp
        net.line.at[5, "in_service"] = False
    except Exception:
        pass


def _apply_fdi_power(tick: int, net):
    if net is None:
        return
    # Liu et al. (2009) BDD-style: perturb 3 bus loads such that chi-squared residual stays low
    # Simplified: scale loads slightly on 3 buses with correlated perturbation
    targets = [2, 5, 10]
    perturbation = np.random.normal(0, 0.05)  # correlated scalar
    for idx in targets:
        try:
            original = float(net.load.at[idx, "p_mw"])
            net.load.at[idx, "p_mw"] = max(0.0, original * (1 + perturbation))
        except Exception:
            pass


def _apply_scada_replay(tick: int, net):
    global _scada_snapshot
    if net is None:
        return
    start_tick = _active.get("scada_replay", {}).get("start_tick", tick)
    replay_offset = tick - start_tick

    if replay_offset == 0:
        # Record snapshot at attack start
        try:
            _scada_snapshot = {
                "line_in_service": net.line["in_service"].copy(),
                "tap_pos":         net.trafo["tap_pos"].copy() if len(net.trafo) > 0 else None,
            }
        except Exception:
            pass
    elif replay_offset >= config.REPLAY_DELAY_TICKS and _scada_snapshot:
        # Restore stale snapshot
        try:
            net.line["in_service"] = _scada_snapshot["line_in_service"].copy()
            if _scada_snapshot["tap_pos"] is not None:
                net.trafo["tap_pos"] = _scada_snapshot["tap_pos"].copy()
        except Exception:
            pass


def _apply_cross_domain_cascade(tick: int, net, attack_state: Dict):
    if net is None:
        return
    start_tick = _active.get("cross_domain_cascade", {}).get("start_tick", tick)
    offset = tick - start_tick

    if offset < 3:
        # Step 1: force traffic signals to all GREEN (synthetic layer signals via attack_state)
        attack_state["traffic_all_green"] = True
    else:
        attack_state.pop("traffic_all_green", None)
        # Step 2: increase power demand on buses 10-15 by 40%
        try:
            bus_loads = net.load[net.load["bus"].isin(range(10, 16))].index
            for idx in bus_loads:
                base = float(net.load.at[idx, "p_mw"])
                net.load.at[idx, "p_mw"] = base * 1.40
        except Exception:
            pass


def _apply_actuator_hijack(tick: int, wn):
    if wn is None:
        return
    try:
        import wntr
        # Enable chemical quality mode if not already
        if wn.options.quality.mode != "CHEMICAL":
            wn.options.quality.mode = "CHEMICAL"
        # Attempt to find chlorine source — Net3 uses "LAKE" as reservoir
        for res_name in wn.reservoir_name_list:
            try:
                res = wn.get_node(res_name)
                # Set initial quality (concentration) to extreme value
                wn.nodes[res_name]["initial_quality"] = config.CHLORINE_MAX * 10
                break
            except Exception:
                pass
    except Exception:
        pass


def _apply_low_slow_recon(tick: int, wn, net):
    """Sub-threshold perturbations designed to stay below CUSUM h=5 for 10+ ticks."""
    affected_water: List[str] = []
    affected_power: List[int] = []

    if wn is not None:
        targets = random.sample(list(wn.junction_name_list), min(5, len(wn.junction_name_list)))
        for nid in targets:
            try:
                node = wn.get_node(nid)
                if node and hasattr(node, "demand_timeseries_list"):
                    for ts in node.demand_timeseries_list:
                        original = ts.base_value
                        ts.base_value = max(0.0, original + np.random.normal(0, 0.5))
                affected_water.append(nid)
            except Exception:
                pass

    if net is not None:
        bus_ids = random.sample(list(net.bus.index), min(5, len(net.bus)))
        loads = net.load[net.load["bus"].isin(bus_ids)].index
        for idx in loads:
            try:
                original = float(net.load.at[idx, "p_mw"])
                net.load.at[idx, "p_mw"] = max(0.0, original + np.random.normal(0, 0.02))
            except Exception:
                pass
        affected_power = [int(b) for b in bus_ids]

    # Store visible-node-mapped affected list so get_affected_nodes() can report SUSPECT nodes
    if "low_and_slow_recon" in _active:
        visible_water = [n for n in affected_water if n in _ALL_WATER_SET]
        visible_power = list({_nearest_visible_power(b) for b in affected_power})
        last = (visible_water + visible_power) or ['15', '40', '4', '12']
        _active["low_and_slow_recon"]["last_affected"] = last


# ---------------------------------------------------------------------------
# Node feedback mapping — city-map node IDs + status for each active attack
# ---------------------------------------------------------------------------

def get_affected_nodes(name: str, tick: int) -> Tuple[List[str], str]:
    """
    Return (city_map_node_ids, status) for the named attack at the given tick.
    Status is 'UNDER_ATTACK' or 'SUSPECT'.  Returns ([], 'UNDER_ATTACK') when inactive.
    """
    if not is_active(name, tick):
        return [], "UNDER_ATTACK"

    entry     = _active.get(name, {})
    start     = entry.get("start_tick", tick)
    offset    = tick - start

    if name == "false_data_injection":
        return ['10', '15', '20'], "UNDER_ATTACK"

    if name == "water_hammer":
        return ['10', '15', '20', '35', '40', '50'], "UNDER_ATTACK"

    if name == "load_redistribution":
        # Line 5 bridges buses 5 and 6 in case33bw; map each to nearest visible power node
        nodes = list({_nearest_visible_power(5), _nearest_visible_power(6)})
        return nodes, "UNDER_ATTACK"

    if name == "false_data_injection_power":
        # Targets buses 2, 5, 10 — map each to nearest visible power node
        nodes = list({_nearest_visible_power(b) for b in [2, 5, 10]})
        return nodes, "UNDER_ATTACK"

    if name == "scada_replay":
        # Stale snapshot replayed across all power lines/transformers
        return list(_ALL_POWER_NODES), "UNDER_ATTACK"

    if name == "cross_domain_cascade":
        if offset < 3:
            # Phase 1: traffic signals forced GREEN
            return list(_ALL_TRAFFIC_NODES), "UNDER_ATTACK"
        else:
            # Phase 2: power buses 10-15 overloaded 40%
            nodes = list({_nearest_visible_power(b) for b in range(10, 16)})
            return nodes, "UNDER_ATTACK"

    if name == "actuator_hijack":
        # Reservoir chlorine injection — affects entire water distribution
        return list(_ALL_WATER_NODES), "UNDER_ATTACK"

    if name == "low_and_slow_recon":
        last = entry.get("last_affected", ['15', '40', '4', '12'])
        return list(last), "SUSPECT"

    if name == "denial_of_service_ot":
        return list(_ALL_WATER_NODES + _ALL_POWER_NODES + _ALL_TRAFFIC_NODES), "UNDER_ATTACK"

    return [], "UNDER_ATTACK"
