# FusionQuad Backend — Architecture Review

> Status: Review findings. Not implementation plan.
> Caveman notation: X -> Y = causality. Strike = delete.

---

## Bug (Fix First)

**WEEKEND rate inconsistency**

| Module | Rate |
|--------|------|
| `tariff/node.py` | 0.30 RM/kWh |
| `optimization/solver.py` | 0.25 RM/kWh |
| `auditor/agent.py` | 0.30 RM/kWh |

Solver uses wrong rate -> MILP cost function wrong -> dispatch suboptimal on weekends/holidays.

---

## Opportunity 1 — God-State AgentState

**Files**: `agents/state.py` + all nodes

**Problem**: 40+ field flat TypedDict. No ownership. Every node reads/writes overlapping fields. New node -> read entire state to understand. Interface = implementation.

**Deletion test**: Delete `AgentState` -> complexity explodes across all nodes. Pass.

**Fix**: Replace flat fields with value objects.

```
BatteryState       { soc, capacity_kwh, cycle_count, temperature_c }
ForecastResult     { load_forecast, confidence, horizon }
TariffContext      { window, energy_rate, demand_charge, tariff_type }
DispatchAction     { action, discharge_kw, charge_kw, duration_min, expected_soc_after }
DispatchResult     { new_soc, temp_increase_c, cycle_count_delta, action_taken }
OptimizationStrategy { strategy_name, shave_kw, reserve_soc_pct, rationale, confidence }
```

AgentState becomes composition of these objects.

**Gain**: Node interface = 1-2 value objects. Tests target object contract. Adding node = define new value object, not read whole state.

---

## Opportunity 2 — Rate Card in 3 Places (Bug Source)

**Files**: `tariff/node.py`, `optimization/solver.py`, `auditor/agent.py`

**Problem**: 3 private rate dicts -> values diverge. Tariff node is authoritative but solver/auditor never read from it. Deletion test: delete tariff node rates -> solver/auditor don't break. Wrong.

**Fix**: Single `TariffRates` source. Solver + Auditor consume `TariffContext` from state (already emitted by tariff node). Delete private copies.

```python
# One source of truth
TARIFF_RATES = {
    "C2": TariffRates(peak=0.45, off_peak=0.22, weekend=0.30, demand=97.06)
}
```

**Gain**: WEEKEND bug fixed. Rate change = 1 edit. Savings accuracy tests meaningful.

---

## Opportunity 3 — Strategy Dict Dual-Shape Convention

**Files**: `planner/node.py`, `controller/node.py`, `optimization/solver.py`

**Problem**: `optimization_strategy` supports 2 field-name shapes simultaneously:
- `strategy_name` OR `strategy`
- `targets.shave_kw` OR `shave_kw`

Controller has `_build_solver_strategy()` flattening both shapes. Every consumer must handle both. Backward-compat shim code masquerading as flexibility.

**Fix**: `OptimizationStrategy` Pydantic model. Single canonical shape. Planner emits it. Controller/Solver consume typed. Delete `_build_solver_strategy()`.

```python
class OptimizationStrategy(BaseModel):
    strategy_name: str
    shave_kw: float
    reserve_soc_pct: float
    target_soc_end: float = 0.50
    rationale: str
    confidence: float
    md_limit_kw: float
```

**Gain**: Planner output testable against schema. Controller drops flattening shim. One shape.

---

## Opportunity 4 — Agent Model Hardcoded 3x

**Files**: `planner/node.py`, `controller/node.py`, `auditor/agent.py`

**Problem**: `"claude-sonnet-4-5-20250929"` string literal in 3 files. Upgrade = 3 edits, no guarantee consistency. Env-driven model selection was a prior feature — drifted back to hardcoded.

**Fix**: Centralized config.

```python
# agents/config.py
AGENT_MODELS = {
    "planner":    os.getenv("PLANNER_MODEL",    "claude-sonnet-4-6"),
    "controller": os.getenv("CONTROLLER_MODEL", "claude-sonnet-4-6"),
    "auditor":    os.getenv("AUDITOR_MODEL",    "claude-sonnet-4-6"),
}
```

**Gain**: Model upgrade = 1 line or env var. Tests swap models without touching agent files.

---

## Opportunity 5 — Prompts Buried in Python

**Files**: `controller/node.py` (`_build_controller_prompt`), `auditor/agent.py` (`_build_tick_prompt`, `_build_eod_prompt`), `planner/node.py`

**Problem**: System prompt = most important interface in Deep Agent. Buried in f-string inside fn. Untestable in isolation. EOD vs tick Auditor prompt = if/else on bool -> two entirely different 30-line strings in same file.

**Fix**: Extract to template files.

```
agents/
  controller/
    prompts/
      system.md
  auditor/
    prompts/
      tick.md
      end_of_day.md
  planner/
    prompts/
      system.md
```

Load at node init. Render with `.format(**context)` or Jinja2.

**Gain**: Prompts reviewable/diffable. Prompt engineers work in `.md`, not Python. EOD/tick split = two files, not if/else.

---

## Opportunity 6 — SimulationService 4 Responsibilities

**File**: `services/simulation.py`

**Problem**: Single class does:
1. Session management
2. Workflow invocation
3. Tick scheduling/autoplay (async)
4. Tick logging (file I/O)
5. Sizing recommendations (static calculation from load profile)

Deletion test on `_compute_sizing_recommendation()`: reappears elsewhere. It's freestanding domain calc, not simulation behavior.

**Fix**: Extract modules.

```
SizingAdvisor   load_profile -> SizingRecommendation
TickLogger      tick_data -> appends to log file
SimulationService  session orchestration only
```

**Gain**: `SizingAdvisor` independently testable/reusable. `TickLogger` swappable (file -> DB). `SimulationService` shrinks to readable size.

---

## Priority Order

| # | Opportunity | Why First |
|---|-------------|-----------|
| 2 | Rate card unification | Bug in prod. Fix now. |
| 3 | OptimizationStrategy Pydantic model | Unblocks clean interfaces. Low risk. |
| 4 | Agent model config | 30-min fix. High leverage. |
| 1 | Value objects for AgentState | Biggest structural win. Do after 2+3. |
| 5 | Prompt templates | High value for maintainability. Medium effort. |
| 6 | SimulationService split | Cleanup. Do last. |

---

## What NOT to Change

- LangGraph StateGraph pipeline structure — works, don't touch
- InMemorySaver checkpointing — works
- Deep Agent + tool pattern — correct architecture
- MILP solver logic — math is right, just rate constants wrong
- RAG via FilesystemBackend — works
- Fallback chain (Deep Agent -> local fn) — good resilience pattern
