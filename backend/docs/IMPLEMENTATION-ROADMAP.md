# FusionQuad — Implementation Roadmap

## Current State vs. Target

The current codebase implements a **linear LangGraph chain** where each node is a deterministic function (not a Deep Agent), with the optimization node calling MILP directly and controller as a separate node.

The target architecture consolidates Controller + MILP into a single Deep Agent, adds RAG-backed experience loops, and introduces time-windowed tick selection.

---

## Phase 1 — Controller + MILP Integration

**Goal**: Controller becomes a Deep Agent that calls MILP as a tool. Optimization node is removed.

### Changes

| File | Change |
|------|--------|
| `backend/app/agents/workflow.py` | Remove `optimization` node; add edge `planner → controller` |
| `backend/app/agents/controller/node.py` | Refactor to Deep Agent; add MILP solver as `@tool` |
| `backend/app/agents/optimization.py` | Remove (functionality merged into controller) |
| `backend/app/agents/optimization/solver.py` | Move into controller as internal tool |
| `backend/app/agents/state.py` | Remove `dispatch_plan` from AgentState |

### MILP Tool Signature (in Controller)

```python
@tool
def milp_optimizer(
    load_forecast: list[float],
    tariff_window: str,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    optimization_strategy: dict,
    previous_dispatch_plan: list[dict] | None,
) -> dict:
    """MILP solver — computes optimal BESS dispatch for this tick."""
```

### Controller System Prompt (updated)

```
You are the Controller Agent for FusionQuad — you execute BESS dispatch actions.

Your workflow:
1. Read the optimization_strategy from state (set by Planner)
2. Call milp_optimizer with current state parameters
3. Receive dispatch_action from MILP
4. Execute dispatch via mock_inverter_dispatch
5. On failure: re-invoke milp_optimizer with adjusted parameters

Never call milp_optimizer without reading optimization_strategy first.
```

---

## Phase 2 — Experience Loop

**Goal**: Auditor writes `.md` reports to `experience/`; Planner can search them via RAG.

### Changes

| File/Directory | Change |
|----------------|--------|
| `backend/experience/` | Create directory; add `.gitkeep` |
| `backend/app/agents/auditor/agent.py` | Add `write_experience_report()` after end-of-day evaluation |
| `backend/app/agents/planner/node.py` | Add `experience/` to FilesystemBackend RAG sources |
| `backend/app/agents/SPEC-planner.md` | Update tools section to include `experience/` |

### Experience File Naming

```
backend/experience/{date}-{day_type}.md
```

Example: `backend/experience/2025-09-01-solar_duck_curve.md`

### Experience File Content

```markdown
# Audit Report — 2025-09-01 (Solar Duck Curve)

## Summary
- Ticks processed: 48
- Within-limit ticks: 42
- Compliance rate: 87.5%
- Total savings: RM 4,850
- Peak shave: 205 kW
- Final SOC: 48%

## Observations
- Morning solar charge was insufficient for afternoon peak
- MILP under-dispatched at tick 28 due to low confidence
- Recommend 200kWh larger BESS for this load profile

## Recommendations
- Increase BESS capacity by 200 kWh
- Target end-of-day SOC at 55% for duck curve days
```

### Planner RAG Sources (updated)

```python
FilesystemBackend(
    dirs=["backend/strategies", "backend/experience"],
    ...
)
```

---

## Phase 3 — Time-Windowed Tick Selection

**Goal**: User can select a start/end datetime within the CSV's available range; only ticks in that window are processed.

### Changes

| File | Change |
|------|--------|
| `backend/app/schemas/simulation.py` | Add `start_time` and `end_time` to `StartSimulationRequest` |
| `backend/app/services/simulation.py` | Map start/end datetime to tick indices; slice interval list |
| `backend/app/agents/data_loader/node.py` | Accept tick range; pass sliced data to downstream nodes |
| `frontend/features/dashboard/data/day-scenarios.ts` | Add `availableDatetimeRange` to day options |
| `frontend/features/dashboard/live-dashboard-page.tsx` | Add datetime range picker UI |
| `frontend/features/dashboard/hooks/use-simulation-controller.ts` | Pass selected time range to API |

### Frontend: DateTime Picker

```typescript
// In the setup panel, below day type selector:
<DateRangePicker
  min={dayOption.availableStart}
  max={dayOption.availableEnd}
  onStartChange={setStartTime}
  onEndChange={setEndTime}
/>
```

### Backend: Tick Windowing Logic

```python
def _ticks_in_window(df: pd.DataFrame, start: datetime, end: datetime) -> list[int]:
    mask = (df["datetime"] >= start) & (df["datetime"] <= end)
    return df[mask].index.tolist()

tick_indices = _ticks_in_window(df, start_time, end_time)
```

---

## Phase 4 — Execution Logging

**Goal**: Every tick appends to a log file; one log file per day.

### Changes

| File/Directory | Change |
|----------------|--------|
| `backend/logs/` | Create directory; add `.gitkeep` |
| `backend/app/services/simulation.py` | After each tick: append to `logs/{date}-{day_type}.json` |
| `backend/app/agents/auditor/agent.py` | At end-of-day: write `audit_report` field to log |

### Log File Format

See `USER-FLOW.md` — "Execution Logs" section.

### Append Logic

```python
import json
from pathlib import Path

def append_tick_log(log_path: Path, tick_data: dict):
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    else:
        log = {"ticks": [], "summary": {}}
    log["ticks"].append(tick_data)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
```

---

## Phase 5 — Tariff Folder + Tavily Update (Future)

**Goal**: Tariff rate cards live in `backend/tariff/` and Planner can use Tavily search to update outdated rates.

### Changes

| File/Directory | Change |
|----------------|--------|
| `backend/tariff/` | Create; add TNB rate card as `.md` file |
| `backend/app/agents/planner/node.py` | Add `tavily_search` tool; allow updating tariff files |

### Tariff File

```
backend/tariff/tnb-rates.md

# TNB Tariff Rates (as of July 2025)

## Demand Charge (MD)
| Tariff | RM/kW/month |
|--------|-------------|
| C1/E1  | 89.27       |
| C2/E2  | 97.06       |

## Energy Charge
| Window   | RM/kWh |
|----------|--------|
| Peak     | 28.52  |
| Off-peak | 22.40  |
```

---

## Full File Tree (Target)

```
backend/
├── agents/
│   ├── __init__.py
│   ├── state.py
│   ├── workflow.py              # [Phase 1] removed optimization node
│   ├── forecast.py              # GRU model wrapper
│   ├── data_loader/
│   │   └── node.py             # [Phase 3] tick windowing
│   ├── tariff/
│   │   └── node.py             # unchanged
│   ├── planner/
│   │   └── node.py             # [Phase 2] + experience/ RAG
│   ├── controller/
│   │   └── node.py             # [Phase 1] Deep Agent + MILP tool
│   └── auditor/
│       └── agent.py            # [Phase 2] write experience/
├── strategies/                 # [Phase 2] RAG source
│   ├── aggressive_peak_shaving.md
│   ├── holiday_surge.md
│   ├── solar_duck_curve.md
│   ├── offpeak_valley_fill.md
│   └── general_bess_guidelines.md
├── experience/                 # [Phase 2] Auditor writes, Planner reads
│   └── .gitkeep
├── tariff/                     # [Phase 5]
│   └── tnb-rates.md
├── logs/                       # [Phase 4]
│   └── .gitkeep
├── services/
│   └── simulation.py           # [Phase 3, 4] tick windowing + logging
├── ml/
│   └── forecast_model.py       # GRU model
└── docs/
    ├── ARCHITECTURE.md
    ├── USER-FLOW.md
    └── IMPLEMENTATION-ROADMAP.md
```

---

## Acceptance Criteria per Phase

### Phase 1 — Controller + MILP
- [ ] `optimization_node` removed from workflow
- [ ] Controller Deep Agent calls MILP as tool
- [ ] Planner output feeds into Controller's MILP call
- [ ] No regression in dispatch output

### Phase 2 — Experience Loop
- [ ] Auditor writes `experience/YYYY-MM-DD-day_type.md` at end of day
- [ ] Planner searches both `strategies/` and `experience/` via RAG
- [ ] Experience files are valid markdown and human-readable

### Phase 3 — Time-Windowed Selection
- [ ] Frontend shows datetime picker populated from CSV metadata
- [ ] Backend processes only ticks within selected window
- [ ] Log file records the selected start/end times

### Phase 4 — Execution Logging
- [ ] One log file created per simulation run
- [ ] Each tick appended to log file
- [ ] End-of-day audit summary written to log

### Phase 5 — Tariff Folder
- [ ] Tariff rates in `backend/tariff/tnb-rates.md`
- [ ] Planner can read and search tariff folder
- [ ] Tavily tool available for updating outdated rates