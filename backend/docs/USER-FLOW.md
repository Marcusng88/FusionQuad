# FusionQuad — User Experience Flow

## Dashboard Overview

The user interacts with FusionQuad through a single-page dashboard that combines live simulation controls, real-time KPIs, and an AI decision trace.

### Page Sections

```
┌─────────────────────────────────────────────────────────────┐
│  [Top] Live Header                                          │
│  - Day scenario label + description                         │
│  - Status (IDLE / PLAYING / PAUSED / COMPLETED)             │
│  - Current tick counter (e.g. "Tick 19 of 48")               │
│  - Current interval time label                              │
│  - Forecast value + confidence                              │
├───────────────────────────┬─────────────────────────────────┤
│  [Left] Setup Controls    │  [Right] Live KPIs              │
│  - Day type selector       │  - Battery SoC                 │
│  - Agentic Mode toggle     │  - Last Dispatch               │
│  - BESS capacity slider    │  - Total Savings               │
│  - Sizing recommendation   │  - Sizing Impact               │
│  - Run / Play / Pause / Step│                               │
│  - Playback speed (1x/10x/60x)│                             │
├───────────────────────────┴─────────────────────────────────┤
│  [Middle] Charts                                            │
│  - SimulationChart (baseline vs optimized load)             │
│  - SoCChart (battery charge level over time)                │
│  - DispatchChart (charge/discharge/hold bars)               │
│  - BaselineChart (raw grid import without BESS)             │
├─────────────────────────────────────────────────────────────┤
│  [Bottom Left] AI Decisions (Agent Trace)                   │
│  - Streaming decision cards per tick                        │
│  - Shows agent name, decision, reason, action               │
│  - Expected kW shaved, estimated savings                    │
├─────────────────────────────────────────────────────────────┤
│  [Bottom Right] Scenario Presets                           │
│  - Card per day type (Weekday / Holiday / Duck / Large)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflows

### Workflow 1: Quick Simulation Run

**Use case**: User wants to see the full day result quickly.

```
1. User selects a day type button (e.g. "Large Facility")
2. User adjusts BESS capacity slider (e.g. 1200 kWh)
3. User optionally toggles "Agentic Mode On"
4. User clicks "Run Optimization"
   → All 48 ticks process sequentially
   → Charts fill progressively
   → AI Decisions panel populates tick by tick
5. Simulation completes → KPI cards show final results
6. Sizing recommendation card may appear (if applicable)
```

### Workflow 2: Live Playback

**Use case**: User wants to watch the simulation run tick by tick.

```
1. User configures day type + BESS capacity + agent mode
2. User clicks "Play"
   → Ticks auto-advance at selected playback speed (1x / 10x / 60x)
   → UI updates in real time
3. User clicks "Pause" to freeze at a specific tick
4. User clicks "Step" to advance one tick manually
```

### Workflow 3: Time-Windowed Simulation

**Use case**: User only wants to simulate a specific window (e.g. peak hours only).

```
1. User selects a day type (e.g. "Solar Duck Curve")
   → System reads actual datetime range from CSV metadata
2. User sees a date/time range picker populated from CSV data
3. User selects start time (e.g. 09:00 AM) and end time (e.g. 03:00 PM)
   → System maps to tick indices 19–31
4. User clicks "Run Optimization"
   → Only 13 ticks are processed
   → Execution log: logs/YYYY-MM-DD-solar_duck_curve-0900-1500.json
```

### Workflow 4: Apply Sizing Recommendation

**Use case**: Simulation completes and shows a sizing recommendation.

```
1. Simulation runs to completion
2. Sizing recommendation card appears:
   "Recommended BESS: 1200 kWh, Solar: 800 kWp, Savings: RM 12,400/mo"
3. User clicks "Use Recommended Size"
   → BESS capacity slider updates to 1200 kWh
   → User can re-run simulation with new capacity
```

---

## Execution Logs

Each simulation run produces one log file per day processed.

### Log file naming

```
logs/{date}-{day_type}.json
```

Example:
```
logs/2025-09-01-solar_duck_curve.json
logs/2025-05-31-weekday.json
logs/2025-07-16-holiday.json
```

### Log structure

```json
{
  "simulation_date": "2025-09-01",
  "day_type": "solar_duck_curve",
  "start_time": "09:00:00",
  "end_time": "15:00:00",
  "ticks_processed": 13,
  "bess_capacity_kwh": 1000,
  "use_deep_agent": true,
  "ticks": [
    {
      "tick": 19,
      "datetime": "2025-09-01T09:00:00",
      "forecast_kw": 720,
      "forecast_confidence": 0.82,
      "tariff_window": "OFF_PEAK",
      "optimization_strategy": { ... },
      "dispatch_action": { "action": "charge", "charge_kw": 150 },
      "dispatch_result": { "new_soc": 0.52, ... },
      "actual_load_kw": 720,
      "within_limit": true,
      "savings_rm": 0.0
    }
  ],
  "summary": {
    "total_ticks": 13,
    "within_limit_ticks": 13,
    "total_savings_rm": 4850.00,
    "peak_shave_kw": 205,
    "compliance_rate": 1.0,
    "final_soc_percent": 48
  },
  "audit_report": "..."
}
```

---

## AI Decision Trace

Each tick produces a `DecisionLog` entry visible in the AI Decisions panel.

### DecisionLog entry

```typescript
{
  timestamp: "2025-09-01 14:00:00",
  agent: "Planner Agent",
  decision: "aggressive_peak_shaving strategy selected",
  reason: "Forecast 920kW exceeds MD limit 800kW. Battery SoC 65% sufficient.",
  action: "Target 120kW shave, discharge 80kW for 30min, reserve 20% SOC",
  expected_reduction_kw: 80,
  estimated_saving_rm: 97.06
}
```

### Agent trace panel

- Cards stream in as ticks are processed
- Color-coded by agent: Forecasting (blue), Planner (green), Controller (orange), Auditor (purple)
- Scrollable — user can review full reasoning trace after completion

---

## BESS Capacity Slider

- **Range**: 500–2000 kWh
- **Default**: 500 kWh
- **Starts at**: 50% SoC
- **Slider update** immediately reflected in state
- No agent re-invocation until user clicks Run/Play

---

## Agentic Mode Toggle

| Mode | Behavior |
|------|----------|
| **Off** (default) | Deterministic fallback — rules-based logic, no LLM calls |
| **On** | Deep Agents activated — ReAct loops with LLM reasoning fire for Planner, Controller, Auditor |

When toggled off during a simulation, the current tick completes in the current mode; subsequent ticks use the new setting.

---

## Sizing Recommendation Card

Appears after simulation completes if sizing engine produces a recommendation.

```
┌─────────────────────────────────────────────┐
│  Sizing Recommendation                      │
│                                             │
│  BESS: 1200 kWh  Solar: 800 kWp             │
│  Est. savings: RM 12,400/month              │
│                                             │
│  Rationale: Current 1000 kWh BESS is       │
│  slightly undersized for this load profile. │
│                                             │
│  [Use Recommended Size]                     │
└─────────────────────────────────────────────┘
```

Clicking "Use Recommended Size" updates `bessCapacityKwh` in state — user can immediately re-run.

---

## Date/Time Range Picker (Time-Windowed Simulation)

Built on top of actual CSV datetime data.

```
1. User selects day type → system loads CSV metadata
2. Date/time range picker shows:
   - Start: min datetime in CSV → max datetime in CSV
   - End:   min datetime in CSV → max datetime in CSV
3. User selects a window (e.g. 09:00–15:00)
4. System maps to tick indices internally
5. Only ticks in window are processed
```

If user selects the full day (00:00–23:30), all 48 ticks run normally.