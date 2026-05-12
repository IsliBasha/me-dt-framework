# ME-DT Framework
## Mythos-Enhanced Digital Twin for Smart City Cyber-Physical Threat Detection

> Bachelor thesis demonstration system — live simulation of the ME-DT framework with real hydraulic, electrical, and AI reasoning components.

---

## Overview

Critical infrastructure in modern smart cities — water distribution networks, power grids, traffic control systems — is increasingly managed through SCADA and Industrial Control System (ICS) layers that were not designed with adversarial intent in mind. As these systems become networked and interconnected, the attack surface expands in ways that traditional, single-domain anomaly detectors cannot fully characterise. A water hammer attack induced by rapid pump toggling looks like noise to a power grid monitor; a subtle false data injection into sensor telemetry evades statistical thresholds designed for steady-state operation.

The ME-DT (Mythos-Enhanced Digital Twin) framework addresses this detection gap by coupling physically accurate infrastructure simulators with a large language model reasoning engine that can articulate *why* a given sensor pattern constitutes a threat, not merely *that* it deviates from baseline. The framework runs three parallel detection strategies — a classical CUSUM sequential test (Page, 1954), an Isolation Forest ensemble (Liu et al., 2008), and the ME-DT AI engine — against the same real-time telemetry stream, enabling a direct, tick-by-tick comparison of time-to-detect and false positive rates across nine distinct attack scenarios.

The physical layer is not synthetic. Water network hydraulics are simulated by WNTR (Klise et al., 2018) running the EPA Net3 benchmark network; the power grid is simulated by pandapower (Thurner et al., 2018) running the IEEE case33bw 33-bus radial distribution feeder. Both simulators solve the underlying differential equations at each tick, so attacks injected into the simulator model produce physically valid anomalous readings rather than scripted telemetry perturbations. The traffic subsystem is a synthetic sine-wave generator used solely to illustrate cross-domain correlation mechanisms; it is clearly labelled SYNTHETIC throughout the system and all outputs.

---

## Architecture

The system is organised into five layers that mirror the proposed ME-DT architecture from the accompanying thesis.

```
Layer 1  Physical Simulation
           ├── Water:   WNTR + Net3.inp (EPA benchmark, 97 nodes, 2 pumps)
           ├── Power:   pandapower + IEEE case33bw (33 buses, 32 branches)
           └── Traffic: Synthetic sine-wave generator [SYNTHETIC — illustrative only]
                 ↓
Layer 2  Data Ingestion
           Normalisation, integrity tagging, per-node anomaly sidecar,
           DoS packet-drop simulation
                 ↓
Layer 3  Digital Twin Core
           Live state vector, rolling 72-tick history, physics validation
           rules (W1–W4 water, P1–P4 power, T1–T2 traffic, X1–X2 cross-domain),
           causal dependency graph, node quarantine
                 ↓ ↕  (asyncio coroutines — never blocks the tick loop)
Layer 4  Mythos AI Engine
           Mode A: continuous threat classification (every tick)
           Mode B: adversarial attack-path probing (every 10 ticks)
           Mode C: zero-day hypothesis generation (gated by confidence < 0.40 + violations)
                 ↓
Layer 5  Response Engine
           Alert routing, auto-quarantine at confidence ≥ 0.92,
           structured event log, TTD comparison report
                 ↓
           FastAPI + WebSocket → dark-mode browser dashboard (Chart.js)
```

### Physics Validation Rules

Layer 3 applies a deterministic rule engine to each tick's state vector independently of the AI layer. This is intentional: the physics rules serve as a ground-truth signal that both informs the AI context prompt and acts as a transparent baseline the examiner can inspect without an API key.

The water rules are: W1 (pump-induced pressure transient on downstream junctions), W2 (per-node adaptive pressure underflow — 2.5σ below rolling baseline with a secondary ramp check that catches low-and-slow attacks evading the sigma path), W3 (rapid pump cycling, a direct water-hammer indicator), and W4 (flow surge above 2× rolling mean). The power rules are: P1 (IEEE 0.90–1.10 pu voltage band violation), P2 (line thermal overload above 100%), P3 (Newton-Raphson load-flow non-convergence sentinel), and P4 (cascade risk: three or more buses with >0.05 pu drop in a single tick). Cross-domain rules X1 and X2 fire when correlated anomalies appear across subsystem boundaries within a short time window, which is the primary ME-DT thesis contribution the framework demonstrates.

### Baseline Detectors

**CUSUM** implements Page's (1954) one-sided cumulative sum with allowance k=0.5 and threshold h=5.0. It operates per-node on the normalised reading stream and is optimal for detecting a single step change in mean. By design it cannot detect distributed, correlated, or ramp-style attacks without a tight threshold that would produce unacceptable false positive rates under normal operating variance.

**Isolation Forest** (Liu et al., 2008) is trained on the joint feature vector of water pressure and power voltage readings, deliberately excluding synthetic traffic data from the feature space. The forest contains 100 trees with contamination fraction 0.05, and is retrained in-place every 20 ticks to track non-stationary baseline drift. It provides a global anomaly score across domains simultaneously, but lacks a causal model and cannot distinguish a voltage violation caused by an attack from one caused by load fluctuation.

**ME-DT** injects the current state snapshot, active physics violations, anomaly sidecar scores, and the running vulnerability atlas into a structured prompt sent to Claude (`claude-sonnet-4-20250514`) via the Anthropic API. The response is parsed as structured JSON into one of three typed output schemas (ThreatAssessment, AttackPath, ZeroDayHypothesis) and broadcast to the dashboard on the following tick. The API call runs as an asyncio task so it never introduces blocking latency into the simulation loop.

---

## Setup

### Requirements

- Python 3.10 or later
- A browser (dashboard is served locally — no deployment required)
- An Anthropic API key for the AI reasoning layer (optional; all other layers function without it)

### Installation

```bash
git clone https://github.com/IsliBasha/me-dt-framework.git
cd me-dt-framework
pip install -r requirements.txt
```

On Ubuntu/Debian with a system-managed Python environment:

```bash
pip install -r requirements.txt --break-system-packages
```

### API Key

Export the Anthropic API key before starting the server:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Without the key the system runs in **demo mode**: all five layers are fully operational, attack injection and baseline detectors work as normal, and the dashboard renders live data, but the AI reasoning panel shows placeholder output rather than real Claude responses. This mode is sufficient to observe the physics simulation and CUSUM/Isolation Forest responses.

### Running

```bash
python main.py
```

Open **http://localhost:8000** in a browser. The WebSocket connection is established automatically on page load and the tick counter begins advancing at 2-second intervals.

---

## Attack Scenarios

Each scenario manipulates the underlying WNTR or pandapower model directly — no telemetry is scripted. The simulator then solves its physical equations against the modified network topology or demand values, producing sensor readings that are anomalous as a natural consequence of the physics.

| Scenario | Severity | Layer | Description |
|---|---|---|---|
| `false_data_injection` | HIGH | WNTR | Zeroes demand on three junctions; pressure response is physically computed |
| `water_hammer` | HIGH | WNTR | Toggles pump status each tick; WNTR produces transient pressure waves |
| `load_redistribution` | CRITICAL | pandapower | Opens line 5; Newton-Raphson converges on a new overloaded topology |
| `false_data_injection_power` | HIGH | pandapower | BDD-style stealthy injection remaining undetected by single-bus monitors |
| `scada_replay` | HIGH | pandapower | Restores a stale topology snapshot, masking the current network state |
| `cross_domain_cascade` | CRITICAL | pandapower | Traffic signal manipulation followed by a correlated power demand surge |
| `actuator_hijack` | CRITICAL | WNTR | Chlorine concentration driven above 4.0 mg/L through injector manipulation |
| `low_and_slow_recon` | MEDIUM | WNTR | Sub-threshold perturbations designed to stay below CUSUM's h=5.0 limit |
| `denial_of_service_ot` | HIGH | Layer 2 | 80% packet drop on the water ingestion stream |

### Injection Methods

**Browser**: Press `A` to open the Attack Console, then click any scenario button.

**CLI**:
```bash
python attacks/inject_attack.py --scenario water_hammer --delay 0
python attacks/inject_attack.py --scenario cross_domain_cascade --delay 5
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/inject-attack \
  -H 'Content-Type: application/json' \
  -d '{"scenario": "low_and_slow_recon", "delay": 0}'
```

---

## Configuration

The key simulation parameters are collected in `config.py` for easy adjustment:

| Parameter | Default | Description |
|---|---|---|
| `TICK_INTERVAL_S` | 2.0 | Seconds per simulation tick |
| `STATE_HISTORY_WINDOW` | 72 | Rolling history depth per node (ticks) |
| `ALERT_THRESHOLD` | 0.75 | ME-DT confidence threshold for alert emission |
| `AUTO_CONTAIN_THRESHOLD` | 0.92 | Confidence level triggering automatic node quarantine |
| `PROBING_INTERVAL_TICKS` | 10 | Ticks between Mode B adversarial probe invocations |
| `CUSUM_K` | 0.5 | CUSUM allowance (reference) parameter |
| `CUSUM_H` | 5.0 | CUSUM detection threshold |
| `ISOFOREST_CONTAMINATION` | 0.05 | Isolation Forest expected contamination fraction |
| `W2_WARMUP_TICKS` | 30 | History entries required before W2 pressure rule activates |
| `W2_SIGMA_THRESHOLD` | 2.5 | Standard deviations below per-node rolling mean to flag |
| `W2_MIN_DROP_M` | 3.0 | Absolute pressure drop (m) triggering the ramp-attack check |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the dashboard |
| WS | `/ws` | Live state broadcast (JSON, every tick) |
| POST | `/api/inject-attack` | Schedule an attack scenario |
| GET | `/api/state` | Current digital twin state snapshot |
| GET | `/api/metrics` | Detector comparison metrics |
| GET | `/api/report` | Export TTD comparison report |
| POST | `/api/reset` | Reset simulation to tick 0 |
| POST | `/api/speed` | Set speed multiplier (0.1–10×) |

---

## Evaluation

The `/api/report` endpoint (also triggered at simulation end) writes three artefacts to the `reports/` directory:

- `metrics_<timestamp>.json` — structured detector metrics including per-scenario time-to-detect, alert counts, and false positive counts for all three detectors
- `comparison_<timestamp>.md` — a formatted TTD comparison table across all attack scenarios
- `events.jsonl` — the full structured event log suitable for post-hoc analysis

The comparison table is the primary evaluation artefact for the thesis. The headline result the framework is designed to demonstrate is the `low_and_slow_recon` row: CUSUM cannot detect it by construction (perturbations are calibrated to remain below h=5.0), Isolation Forest detection is significantly delayed, and ME-DT's cross-domain reasoning identifies the systematic scanning pattern from the correlation of anomalies across subsystems.

---

## Testing

The test suite covers the physics rule engine, ingestion layer, AI mode gating, and metrics export:

```bash
python -m pytest tests/ -v
```

All 74 tests should pass. The W2 adaptive baseline tests (`test_layer3_w2_adaptive.py`, `test_layer3_w2_fixes.py`) are worth reviewing alongside the W2 rule implementation in `layers/layer3_twin.py` — they document the two key design invariants: that the current reading is never part of its own reference distribution (HIGH-1), and that a 0.1 m/tick pressure ramp that evades the sigma path is still detected via the absolute oldest-vs-current drop check (HIGH-2).

---

## Project Structure

```
me-dt-framework/
├── main.py                   # FastAPI server, simulation loop, WebSocket broadcast
├── config.py                 # All tunable parameters
├── models/
│   ├── state_vector.py       # Typed dataclasses: NodeReading, PhysicsViolationEvent, etc.
│   └── threat_model.py       # Threat taxonomy and classification schema
├── layers/
│   ├── layer1_physical.py    # WNTR + pandapower tick execution
│   ├── layer2_ingestion.py   # Normalisation, integrity, anomaly sidecar, DoS simulation
│   ├── layer3_twin.py        # Digital twin state, physics rules, causal graph
│   ├── layer4_mythos.py      # Anthropic API client, Mode A/B/C prompt construction
│   └── layer5_response.py    # Alert routing, auto-quarantine, report generation
├── attacks/
│   ├── scenario_library.py   # Nine attack implementations (mutate wn/net directly)
│   └── inject_attack.py      # CLI injection helper
├── baselines/
│   ├── cusum.py              # Per-node CUSUM (Page, 1954)
│   └── isoforest.py          # Isolation Forest wrapper (Liu et al., 2008)
├── networks/
│   └── Net3.inp              # EPA WNTR benchmark network
├── static/                   # Dashboard HTML, CSS, JS (Chart.js, WebSocket client)
├── tests/                    # pytest test suite (74 tests)
└── reports/                  # Generated TTD reports (written at simulation end)
```

---

## Limitations and Known Issues

The thesis acknowledges three primary limitations that are worth being explicit about here as well.

First, LLM inference latency means ME-DT results arrive one to two ticks behind real-time. For a 2-second tick interval this represents a 2–4 second detection lag relative to the physics rules. In an operational deployment this would need to be weighed against the qualitative richness of the AI output.

Second, the traffic subsystem is explicitly synthetic. The cross-domain rules that use traffic data (T1, T2, X1) are illustrative of how such correlations *would* behave with a real traffic data source such as SUMO or MATSim, but no detection claims in the thesis rely solely on traffic-derived signals.

Third, the attack surface of the LLM prompt itself has not been formally analysed. An adversary with write access to sensor telemetry could in principle attempt to influence the AI output through carefully crafted sensor values — a form of indirect prompt injection that statistical baselines are immune to. This is noted as a direction for future work.

---

## References

- Page, E.S. (1954). Continuous Inspection Schemes. *Biometrika*, 41(1/2), 100–115.
- Liu, F.T., Ting, K.M., Zhou, Z.H. (2008). Isolation Forest. In *Proceedings of the 8th IEEE International Conference on Data Mining* (ICDM 2008), 413–422.
- Liu, Y., Ning, P., Reiter, M.K. (2011). False data injection attacks against state estimation in electric power grids. *ACM Transactions on Information and System Security*, 14(1), 1–33.
- Klise, K.A., Murray, R., Haxton, T. (2018). *An Overview of the Water Network Tool for Resilience (WNTR)*. U.S. EPA Office of Research and Development, EPA/600/R-18/268.
- Thurner, L., Scheidler, A., Schafer, F., et al. (2018). pandapower — An Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems. *IEEE Transactions on Power Systems*, 33(6), 6510–6521.
- Anthropic (2024). Claude: A Family of Foundation Models. Model used: `claude-sonnet-4-20250514`.
