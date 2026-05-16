# FusionQuad — Multi-Agent Architecture

## Overview

FusionQuad is an agentic BESS (Battery Energy Storage System) peak shaving system driven by a multi-agent cognitive control loop. It processes 30-minute energy interval data, forecasts load, plans optimal dispatch, executes BESS actions, and audits results — with learning across sessions.

---

## Agent Inventory

| Agent | Type | Role |
|-------|------|------|
| **Forecaster** | ML (GRU) | Rolling load prediction per tick |
| **Planner** | Deep Agent (ReAct) | Strategic dispatch plan from RAG-backed guidelines |
| **Controller** | Deep Agent (ReAct) | Executes dispatch; calls MILP as a tool |
| **Auditor** | Deep Agent (ReAct) | Evaluates actions; writes experience reports |
| **Tariff** | Config/Module | Computes tariff window and rates (not an agent) |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PER-TICK LOOP  (N ticks)                     │
│                                                                 │
│  data_loader                                                     │
│       │                                                          │
│       ▼                                                          │
│  Forecaster (GRU ML model)                                       │
│       │                                                          │
│       ├── forecast_kw (point estimate)                          │
│       └── forecast_confidence (MAPE-derived)                    │
│       ▼                                                          │
│  Tariff Node (config — computes PEAK/OFF_PEAK/WEEKEND)           │
│       │                                                          │
│       ▼                                                          │
│  Planner (Deep Agent — ReAct loop)                               │
│       │                                                          │
│       ├── RAG search: strategies/  (active strategy)            │
│       ├── RAG search: experience/  (historical audits)           │
│       └── optimization_strategy dict output                      │
│       ▼                                                          │
│  Controller (Deep Agent — ReAct loop)                            │
│       │                                                          │
│       ├── reads optimization_strategy                            │
│       └── calls MILP solver as tool                             │
│       ▼                                                          │
│  MILP Solver                                                     │
│       │                                                          │
│       ├── receives: load_forecast, tariff_window, battery_soc,  │
│       │            bess_capacity_kwh, md_limit_kw, strategy     │
│       └── returns: dispatch_action {action, kW, duration}       │
│       ▼                                                          │
│  LangChain BESS Middleware                                       │
│       │                                                          │
│       ├── dispatches to mock inverter                            │
│       ├── success  → log execution → next tick                  │
│       └── failure   → re-invoke Controller → fix dispatch        │
│       ▼                                                          │
│  Execution log (appended per tick)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    END-OF-DAY                                   │
│                                                                 │
│  Auditor Agent (Deep Agent — ReAct loop)                         │
│       │                                                          │
│       ├── reads: all tick execution logs                        │
│       ├── reads: experience/  (past audit reports)               │
│       └── writes: audit report → experience/                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## RAG Knowledge Sources

Accessible to Planner and Auditor via search tools:

| Directory | Contents | Used By |
|-----------|----------|---------|
| `backend/strategies/` | Strategy guidelines (.md): peak shaving, duck curve, holidays, SOC rules | Planner |
| `backend/experience/` | Auditor's past audit reports (`.md`), one per day | Planner, Auditor |
| `backend/tariff/` | Rate cards, TNB tariff structure | Planner (read-only; can update when outdated) |

---

## Agent Detail

### Forecaster — ML Model (not an agent)

- **Model**: GRU neural network (`app/ml/forecast_model.py`)
- **Sequence length**: 48 intervals (24 hours of history)
- **Horizon**: 6 intervals ahead (3 hours)
- **Per-tick behavior**: Uses all actuals available up to current tick as input; rolling window shifts forward each tick
- **Confidence**: Derived from MAPE on holdout validation split

### Planner — Deep Agent

- **Type**: `create_deep_agent` with ReAct loop + FilesystemBackend (RAG)
- **Tools**: `search_guidelines`, `read_guideline_file`, `get_forecast_context`
- **Input**: forecast, forecast_confidence, tariff_window, day_type, battery_soc, cycle_count
- **Output**: `optimization_strategy` dict
- **RAG**: Searches `strategies/` and `experience/` on every tick

### Controller — Deep Agent with MILP as Tool

- **Type**: `create_deep_agent` with ReAct loop
- **Tool**: `mock_inverter_dispatch` (BESS simulation)
- **Behavior**: Reads `optimization_strategy` from Planner → invokes MILP solver → executes dispatch via middleware → retries on failure
- **Safety**: If battery_soc < 20%, forces "hold"

### Auditor — Deep Agent

- **Type**: `create_deep_agent` with ReAct loop
- **Input**: dispatch_result, dispatch_action, baseline_load, actual_load, battery_soc, tariff_window
- **Evaluation tools**:
  1. `evaluate_rules_tool` — safety checks (always runs)
  2. `evaluate_delta_tool` — numeric scoring (always runs)
  3. `write_experience_report` — appends to experience file
- **Deep Agent reasoning**: Provides reasoning/recommendation as part of its response directly
- **Output**: `decision_log` per tick, end-of-day audit report
- **Experience**: Writes `.md` report to `experience/` at end of day

### Tariff Node — Config Module

- **Input**: `current_time` datetime
- **Output**: `tariff_window` (PEAK / OFF_PEAK / WEEKEND), energy_rate, demand_charge
- **Logic**: Weekdays 14:00–22:00 = PEAK, weekends/holidays = WEEKEND, else OFF_PEAK
- **Holiday lookup**: `backend/data/holidays.json`

---

## Tick Processing Model

- **Interval duration**: 30 minutes
- **Ticks per day**: 48 (full day)
- **Tick selection**: User can select a start/end time within the available date range in the CSV. Only ticks within the window are processed.
- **Rolling forecast**: Each tick's forecast uses all actuals from previous ticks as context. Accuracy improves through the day.
- **Checkpointing**: LangGraph `InMemorySaver` allows pause/resume at any tick

---

## Data Files

| File | Day Type | Description |
|------|----------|-------------|
| `1. Load Profile (With Solar Installed) SoL.csv` | solar_duck_curve | Sep 1, 2025 — post-solar duck curve ramp |
| `2. Load Profile (No Solar) E.csv` | weekday | May 31, 2025 — weekday baseline |
| `3. Load Profile (No Solar) SuN.csv` | holiday | Sunday/holiday high-demand scenario |
| `4. Load Profile (With Solar) Mi2.csv` | large_weekday | Large facility (1000–1400 kW) with solar |

---

## BESS Dispatch Actions

| Action | Meaning |
|--------|---------|
| `discharge` | Battery releases stored energy to grid (reduces import) |
| `charge` | Battery absorbs excess solar/cheap energy |
| `hold` | No dispatch — battery idle |

---

## MILP Cost Function

```
Minimize: (energy_imported × RM/kWh) + (peak_demand_kW × RM/kW) + (battery_degradation_cost)

Subject to:
  - SOC limits: 0.20 ≤ SOC ≤ 0.95
  - Charge/discharge power ≤ BESS rated power
  - Demand limit: grid_import ≤ 800 kW (md_limit_kw)
  - End-of-day target SOC (configurable, default 50%)
```

---

## Key State Fields (AgentState)

| Field | Description |
|-------|-------------|
| `day_type` | Selected scenario: weekday / holiday / solar_duck_curve / large_weekday |
| `battery_soc` | Current battery state-of-charge (0–1) |
| `bess_capacity_kwh` | Installed BESS capacity |
| `load_forecast` | Forecast kW per facility for next horizon |
| `forecast_confidence` | MAPE-derived confidence (0–1) |
| `tariff_window` | PEAK / OFF_PEAK / WEEKEND |
| `optimization_strategy` | Planner's strategic dispatch directive |
| `dispatch_action` | MILP's computed action for current tick |
| `dispatch_result` | BESS middleware's execution result |
| `decision_log` | Accumulated auditor entries across ticks |