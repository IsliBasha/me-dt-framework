"""
Layer 1 — Physical Infrastructure
Provides: water (WNTR/Net3), power (pandapower/case33bw), traffic (synthetic)
"""

import copy
import hashlib
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import numpy as np

import config

# ---------------------------------------------------------------------------
# WNTR / pandapower loaded lazily so import errors surface clearly
# ---------------------------------------------------------------------------
try:
    import wntr
    _WNTR_OK = True
except ImportError:
    _WNTR_OK = False
    print("[Layer1] WARNING: wntr not installed — water simulation disabled")

try:
    import pandapower as pp
    import pandapower.networks as pn
    _PP_OK = True
except ImportError:
    _PP_OK = False
    print("[Layer1] WARNING: pandapower not installed — power simulation disabled")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _integrity_hash(node_id: str, value: float, timestamp_ms: int) -> str:
    raw = f"{node_id}{value}{timestamp_ms}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Water subsystem
# ---------------------------------------------------------------------------

def init_water_network():
    """Copy bundled Net3.inp to networks/ if needed, return a WaterNetworkModel."""
    if not _WNTR_OK:
        return None
    os.makedirs("networks", exist_ok=True)
    if not os.path.exists(config.WATER_NETWORK_FILE):
        import shutil
        bundled = os.path.join(os.path.dirname(wntr.__file__), "library", "networks", "Net3.inp")
        if os.path.exists(bundled):
            shutil.copy(bundled, config.WATER_NETWORK_FILE)
            print(f"[Layer1] Net3.inp copied from wntr bundle to {config.WATER_NETWORK_FILE}")
        else:
            print(f"[Layer1] Downloading Net3.inp from WNTR GitHub...")
            urllib.request.urlretrieve(config.NET3_URL, config.WATER_NETWORK_FILE)
            print(f"[Layer1] Net3.inp saved to {config.WATER_NETWORK_FILE}")

    wn = wntr.network.WaterNetworkModel(config.WATER_NETWORK_FILE)
    wn.options.time.duration = 0
    wn.options.time.hydraulic_timestep = max(1, int(config.TICK_INTERVAL_S))
    return wn


def run_water_tick(wn, attack_state: Dict) -> Dict:
    """Run one WNTR hydraulic simulation step and return telemetry dict."""
    if not _WNTR_OK or wn is None:
        return {}
    ts_ms = _now_ms()
    ts_iso = _iso_now()

    try:
        # Deep-copy wn so each tick gets a fresh hydraulic time state.
        # WNTRSimulator exhausts duration=0 after one call; reusing the same
        # object returns an empty result frame from tick 1 onwards.
        wn_snap = copy.deepcopy(wn)
        sim = wntr.sim.WNTRSimulator(wn_snap)
        results = sim.run_sim()
    except Exception as e:
        print(f"[Layer1] WNTR sim error: {e}")
        return {}

    telemetry: Dict[str, Any] = {}

    try:
        pressure = results.node["pressure"]
        head     = results.node["head"]
        demand   = results.node["demand"]
        flowrate = results.link["flowrate"]
        velocity = results.link["velocity"]
    except Exception:
        return {}

    for node_id in config.WATER_DISPLAY_NODES:
        try:
            node_obj = wn.get_node(node_id)
            if node_obj is None:
                continue
        except Exception:
            continue
        try:
            p_val = max(0.0, float(pressure.loc[0, node_id])) if node_id in pressure.columns else 0.0
        except Exception:
            p_val = 0.0
        telemetry[node_id] = {
            "pressure":       p_val,
            "unit":           "m",
            "status":         "NORMAL",
            "subsystem":      "water",
            "source":         "SIMULATED",
            "timestamp_ms":   ts_ms,
            "timestamp_iso":  ts_iso,
            "integrity_hash": _integrity_hash(node_id, p_val, ts_ms),
        }

    # Include all nodes for Layer 2 processing
    for node_id in list(wn.junction_name_list):
        if node_id in telemetry:
            continue
        try:
            p_val = max(0.0, float(pressure.loc[0, node_id])) if node_id in pressure.columns else 0.0
        except Exception:
            p_val = 0.0
        telemetry[node_id] = {
            "pressure":       p_val,
            "unit":           "m",
            "status":         "NORMAL",
            "subsystem":      "water",
            "source":         "SIMULATED",
            "timestamp_ms":   ts_ms,
            "timestamp_iso":  ts_iso,
            "integrity_hash": _integrity_hash(node_id, p_val, ts_ms),
        }

    # Pump telemetry — value 1.0=Open, 0.0=Closed so W3 can detect toggles
    for pump_id in wn_snap.pump_name_list:
        try:
            pump = wn_snap.get_link(pump_id)
            raw_status = getattr(pump, "initial_status", None)
            is_open = raw_status == wntr.network.LinkStatus.Open
            status_val = 1.0 if is_open else 0.0
            telemetry[f"pump_{pump_id}"] = {
                "value":         status_val,
                "unit":          "",
                "status":        str(raw_status),
                "subsystem":     "water",
                "pump":          True,
                "timestamp_ms":  ts_ms,
                "timestamp_iso": ts_iso,
                "integrity_hash": _integrity_hash(f"pump_{pump_id}", status_val, ts_ms),
            }
        except Exception as e:
            print(f"[Layer1] pump {pump_id} telemetry error: {e}")

    return telemetry


# ---------------------------------------------------------------------------
# Power subsystem
# ---------------------------------------------------------------------------

def init_power_network():
    """Create and return the IEEE 33-bus radial distribution network."""
    if not _PP_OK:
        return None, None, None
    net = pn.case33bw()
    orig_impedances = net.line[["r_ohm_per_km", "x_ohm_per_km"]].copy()
    orig_loads = net.load[["p_mw", "q_mvar"]].copy()
    return net, orig_impedances, orig_loads


def run_power_tick(net, attack_state: Dict) -> Dict:
    """Run one pandapower load flow and return telemetry dict."""
    if not _PP_OK or net is None:
        return {}
    ts_ms = _now_ms()
    ts_iso = _iso_now()

    collapsed = False
    try:
        pp.runpp(net, algorithm="nr", numba=False)
    except Exception:
        collapsed = True

    telemetry: Dict[str, Any] = {}

    if collapsed:
        for bus_id in config.POWER_DISPLAY_BUSES:
            telemetry[str(bus_id)] = {
                "vm_pu":         0.0,
                "va_degree":     0.0,
                "p_mw":          0.0,
                "q_mvar":        0.0,
                "loading_pct":   0.0,
                "status":        "GRID_COLLAPSE",
                "subsystem":     "power",
                "source":        "SIMULATED",
                "timestamp_ms":  ts_ms,
                "timestamp_iso": ts_iso,
                "integrity_hash": _integrity_hash(str(bus_id), 0.0, ts_ms),
            }
        telemetry["__grid_collapse__"] = True
        return telemetry

    for bus_id in config.POWER_DISPLAY_BUSES:
        try:
            vm   = float(net.res_bus.at[bus_id, "vm_pu"])
            va   = float(net.res_bus.at[bus_id, "va_degree"])
            p    = float(net.res_bus.at[bus_id, "p_mw"])
            q    = float(net.res_bus.at[bus_id, "q_mvar"])
        except Exception:
            vm, va, p, q = 1.0, 0.0, 0.0, 0.0

        # Line loading for this bus (first adjacent line)
        loading = 0.0
        try:
            mask = net.line["from_bus"] == bus_id
            if mask.any():
                idx = net.line[mask].index[0]
                loading = float(net.res_line.at[idx, "loading_percent"])
        except Exception:
            pass

        telemetry[str(bus_id)] = {
            "vm_pu":         vm,
            "va_degree":     va,
            "p_mw":          p,
            "q_mvar":        q,
            "loading_pct":   loading,
            "status":        "NORMAL",
            "subsystem":     "power",
            "source":        "SIMULATED",
            "timestamp_ms":  ts_ms,
            "timestamp_iso": ts_iso,
            "integrity_hash": _integrity_hash(str(bus_id), vm, ts_ms),
        }

    # All buses for Layer 2 processing
    for bus_id in net.bus.index:
        bid = str(bus_id)
        if bid in telemetry:
            continue
        try:
            vm = float(net.res_bus.at[bus_id, "vm_pu"])
        except Exception:
            vm = 1.0
        telemetry[bid] = {
            "vm_pu":         vm,
            "status":        "NORMAL",
            "subsystem":     "power",
            "source":        "SIMULATED",
            "timestamp_ms":  ts_ms,
            "timestamp_iso": ts_iso,
            "integrity_hash": _integrity_hash(bid, vm, ts_ms),
        }

    return telemetry


# ---------------------------------------------------------------------------
# Traffic subsystem (synthetic — explicitly labeled)
# ---------------------------------------------------------------------------

_TRAFFIC_PHASES  = np.random.uniform(0, 2 * np.pi, config.TRAFFIC_NODE_COUNT)
_TRAFFIC_OFFSETS = np.random.uniform(0, 90, config.TRAFFIC_NODE_COUNT)
_DAILY_PERIOD    = 720
_A               = 150.0
_SIGNAL_CYCLE    = 90   # total signal cycle in ticks


def run_traffic_tick(tick: int) -> Dict:
    """Generate synthetic traffic telemetry for 12 intersection nodes."""
    ts_ms  = _now_ms()
    ts_iso = _iso_now()
    telemetry: Dict[str, Any] = {}

    for i in range(config.TRAFFIC_NODE_COUNT):
        node_id = f"SYN-T{i+1:02d}"
        vehicle_flow = float(
            _A * np.sin(2 * np.pi * tick / _DAILY_PERIOD + _TRAFFIC_PHASES[i])
            + np.random.normal(0, 15)
        )
        vehicle_flow = max(0.0, vehicle_flow)

        # Signal phase cycling: GREEN(45s) / YELLOW(5s) / RED(40s)
        offset_tick   = (tick + int(_TRAFFIC_OFFSETS[i])) % _SIGNAL_CYCLE
        if offset_tick < 45:
            signal_phase = "GREEN"
        elif offset_tick < 50:
            signal_phase = "YELLOW"
        else:
            signal_phase = "RED"

        queue_length  = max(0.0, vehicle_flow * 0.3 + np.random.normal(0, 5))
        travel_time_s = max(10.0, 60.0 - vehicle_flow * 0.15 + np.random.normal(0, 3))

        telemetry[node_id] = {
            "vehicle_flow":   round(vehicle_flow, 2),
            "signal_phase":   signal_phase,
            "queue_length":   round(queue_length, 2),
            "travel_time_s":  round(travel_time_s, 2),
            "unit":           "veh/min",
            "subsystem":      "traffic",
            "source":         "SYNTHETIC",
            "status":         "NORMAL",
            "timestamp_ms":   ts_ms,
            "timestamp_iso":  ts_iso,
            "integrity_hash": _integrity_hash(node_id, vehicle_flow, ts_ms),
        }

    return telemetry


# ---------------------------------------------------------------------------
# Combined batch
# ---------------------------------------------------------------------------

def run_tick(tick: int, wn, net, attack_state: Dict) -> Dict:
    water   = run_water_tick(wn, attack_state)
    power   = run_power_tick(net, attack_state)
    traffic = run_traffic_tick(tick)
    return {
        "tick":         tick,
        "timestamp_ms": _now_ms(),
        "water":        water,
        "power":        power,
        "traffic":      traffic,
    }


# ---------------------------------------------------------------------------
# Self-test — print one tick to confirm both simulators work
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Layer 1 self-test ===")
    wn_ = init_water_network()
    net_, _, _ = init_power_network()
    batch = run_tick(0, wn_, net_, {})
    print(f"\nTick 0 — Water nodes ({len(batch['water'])} total):")
    for nid in config.WATER_DISPLAY_NODES:
        nd = batch["water"].get(nid, {})
        p = nd.get("pressure", None)
        print(f"  {nid:20s}  pressure={p:.2f} m" if p is not None else f"  {nid:20s}  (missing)")
    print(f"\nTick 0 — Power buses ({len(batch['power'])} total):")
    for bid in config.POWER_DISPLAY_BUSES:
        bd = batch["power"].get(str(bid), {})
        print(f"  bus {bid:2d}  vm_pu={bd.get('vm_pu', '?'):.4f}  loading={bd.get('loading_pct', 0):.1f}%")
    print(f"\nTick 0 — Traffic (SYNTHETIC) nodes: {len(batch['traffic'])}")
    for nid in list(batch["traffic"].keys())[:3]:
        td = batch["traffic"][nid]
        print(f"  {nid}  flow={td['vehicle_flow']:.1f} veh/min  phase={td['signal_phase']}")
    print("\n[Layer1] Self-test PASSED")
