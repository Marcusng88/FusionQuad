# Plan: User-Configurable MD Limit + MILP Objective Fix

## Goals
1. Let user set `md_limit_kw` and `max_discharge_kw` before starting a simulation
2. Fix MILP solver objective (currently minimizes discharge — should minimize peak demand)
3. Expose `max_discharge_kw` through the full stack (schema → state → solver)

---

## Root Problems Being Fixed

| Problem | File | Impact |
|---|---|---|
| `md_limit_kw` hardcoded in data_loader, no user entry point | `data_loader/node.py:110` | User can't change MD limit |
| `StartSimulationRequest` has no `md_limit_kw` field | `schemas/simulation.py` | API rejects user value |
| MILP objective minimizes discharge (backwards) | `solver.py:119` | Solver avoids discharging during PEAK |
| `MAX_DISCHARGE_KW = 100` hardcoded constant | `solver.py:48` | Planner's 200+ kW shave target silently ignored |
| Planner system prompt anchors to `800.0` in example JSON | `system.md` | LLM ignores state md_limit even when different |
| `"Not Solved"` MILP status treated as success | `solver.py:144` | CBC timeout → None values → 0 kW dispatch |

---

## Implementation Order

### Step 1 — Backend schema + state (foundation, no logic changes)

**`backend/app/schemas/simulation.py`**
- Add to `StartSimulationRequest`:
  ```python
  md_limit_kw: float = Field(default=800.0, gt=0, description="Maximum demand limit in kW")
  max_discharge_kw: float | None = Field(default=None, gt=0, description="Max BESS discharge rate kW; defaults to bess_capacity_kwh (1C)")
  ```

**`backend/app/agents/state.py`**
- Add `max_discharge_kw: float` to `AgentState` TypedDict (default 500.0)

---

### Step 2 — Remove md_limit_kw ownership from data_loader

**`backend/app/agents/data_loader/node.py`**
- Remove line: `"md_limit_kw": DEFAULT_MD_LIMIT_KW` from the return dict
- Keep `DEFAULT_MD_LIMIT_KW` constant (still used in `simulation.py` window scoring at line 510)

**`backend/app/services/simulation.py`**
- Add params to `start()`:
  ```python
  md_limit_kw: float = 800.0,
  max_discharge_kw: float | None = None,
  ```
- After `state = {**loaded, ...}`, inject user values so they override anything data_loader set:
  ```python
  state["md_limit_kw"] = md_limit_kw
  state["max_discharge_kw"] = max_discharge_kw or bess_capacity_kwh
  ```
- Pass both from the API router through to `service.start()`

**`backend/app/routers/` (wherever `/api/v1/simulation/start` lives)**
- Pass `request.md_limit_kw` and `request.max_discharge_kw` to `service.start()`

---

### Step 3 — Fix MILP solver

**`backend/app/agents/optimization/solver.py`**

#### 3a. Add `max_discharge_kw` to OptimizationInput
```python
@dataclass
class OptimizationInput:
    ...
    max_discharge_kw: float = 100.0   # new field
```

#### 3b. Fix MILP variable bounds (use input value, not constant)
```python
# Before:
power = [pulp.LpVariable(f"power_{i}", -MAX_CHARGE_KW, MAX_DISCHARGE_KW) ...]

# After:
max_d = input_data.max_discharge_kw
power = [pulp.LpVariable(f"power_{i}", -MAX_CHARGE_KW, max_d) ...]
```

#### 3c. Fix objective — minimize peak demand, not discharge
```python
# Before (wrong):
energy_cost = sum(energy_rate * power[i] * (DT_SECONDS / 3600) for i in range(n_intervals))
prob += energy_cost

# After (correct):
peak_demand = pulp.LpVariable("peak_demand", lowBound=0)
for i in range(n_intervals):
    if input_data.tariff_window == "PEAK":
        prob += peak_demand >= input_data.load_forecast[i] - power[i]

energy_cost = pulp.lpSum(energy_rate * power[i] * (DT_SECONDS / 3600) for i in range(n_intervals))
# MD penalty weight 100 makes peak_demand reduction dominate over energy cost
prob += 100.0 * peak_demand + energy_cost
```

Why weight=100: MD charge is RM 97.06/kW vs energy RM 0.234/kWh. The ratio is ~415x. Using 100 makes the objective heavily favor peak shaving without overflowing MILP numerics. Doesn't need to be exact RM — it's a relative weight.

#### 3d. Fix infeasibility check
```python
# Before:
if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):

# After:
if pulp.LpStatus[prob.status] != "Optimal":
```

"Not Solved" (CBC timeout) must fall to `_fallback_discharge`, not proceed with None values.

#### 3e. Remove `MAX_DISCHARGE_KW` and `MAX_CHARGE_KW` module-level constants
Replace all usages with `input_data.max_discharge_kw` / `input_data.max_charge_kw`. Keep `MIN_SOC`, `MAX_SOC`, `DT_SECONDS` — those are physics, not config.

---

### Step 4 — Wire max_discharge_kw through controller

**`backend/app/agents/controller/node.py`**

- Read from state at top of `controller_node()`:
  ```python
  max_discharge_kw = float(state.get("max_discharge_kw") or bess_capacity_kwh)
  ```

- Pass to `milp_optimizer` tool call (add param to the tool):
  ```python
  @tool
  def milp_optimizer(
      ...
      max_discharge_kw: float = 500.0,   # new
  ) -> dict:
  ```
  Pass through to `OptimizationInput(max_discharge_kw=max_discharge_kw, ...)`

- Pass to `_local_milp_fallback()` (add param there too)

- Fix MD override cap (currently hardcoded 100):
  ```python
  # Before:
  min_discharge_kw = min(baseline_load - md_limit_kw + 15.0, 100.0)

  # After:
  min_discharge_kw = min(baseline_load - md_limit_kw + 15.0, max_discharge_kw)
  ```

---

### Step 5 — Fix planner prompt anchor

**`backend/app/agents/planner/prompts/system.md`**

In the Output Format section, change example JSON:
```json
// Before:
"md_limit_kw": 800.0,

// After:
"md_limit_kw": <use the md_limit_kw value from the STATE block above — do not default to 800>,
```

Also remove the hardcoded `800` from the MANDATORY PEAK OVERRIDE code block — replace with `md_limit_kw` variable reference.

---

### Step 6 — Frontend: editable config in setup-section

**`frontend/features/dashboard/components/setup-section.tsx`**

Change from static display to controlled inputs. Use inline edit (Option A — simpler, fits existing ConfigCard layout):

```tsx
// Before:
<ConfigCard
  title="Tariff configuration"
  fields={[
    ["Demand limit", "800 kW"],
    ...
  ]}
/>

// After: accept props and render inputs
interface SetupSectionProps {
  mdLimitKw: number;
  maxDischargeKw: number;
  onMdLimitChange: (v: number) => void;
  onMaxDischargeChange: (v: number) => void;
}
```

Fields that become inputs:
- `Demand limit` → number input, min=100, max=2000, step=50, suffix "kW"
- `Max discharge` → number input, min=50, max=2000, step=50, suffix "kW"

Fields that stay static (not user config):
- MD rate (RM 97.06 — TNB tariff, not configurable)
- Peak start/end (14:00–22:00 — fixed for TNB C2)
- Reserve floor (20% — safety constraint)
- Battery capacity (already in `bess_capacity_kwh` on the simulation form)

**`frontend/features/dashboard/live-dashboard-page.tsx`**

Add state:
```tsx
const [mdLimitKw, setMdLimitKw] = useState(800);
const [maxDischargeKw, setMaxDischargeKw] = useState(500);
```

Pass to `SetupSection` as props. Pass to API call:
```tsx
body: JSON.stringify({
  ...existingFields,
  md_limit_kw: mdLimitKw,
  max_discharge_kw: maxDischargeKw,
})
```

---

## Files Changed Summary

```
backend/app/schemas/simulation.py          add md_limit_kw, max_discharge_kw to request
backend/app/agents/state.py                add max_discharge_kw field
backend/app/agents/data_loader/node.py     remove md_limit_kw from return dict
backend/app/services/simulation.py         add params, inject into state after loaded spread
backend/app/routers/<simulation router>    pass new fields to service.start()
backend/app/agents/optimization/solver.py  fix objective, expose max_discharge_kw, fix infeasibility check
backend/app/agents/controller/node.py      read max_discharge_kw, pass to solver, fix MD override cap
backend/app/agents/planner/prompts/system.md  remove 800 anchor from example

frontend/features/dashboard/components/setup-section.tsx   editable inputs with props
frontend/features/dashboard/live-dashboard-page.tsx         state + API call update
```

**Not changing:**
- `agents/planner/node.py` — `parsed.get("md_limit_kw", 800.0)` is fine; planner echoes state's value in its JSON output. The 800.0 fallback only activates if planner fails to include it, which means state value is already set correctly upstream.
- `agents/auditor/` — reads `md_limit_kw` from state directly, no hardcoded value issue
- All ML/forecast code — not related

---

## What This Fixes

| Before | After |
|---|---|
| User can't change MD limit | Number input in setup card, flows to all agents |
| Solver caps discharge at 100 kW regardless | Discharge cap = user's max_discharge_kw value |
| MILP actively avoids discharging | MILP minimizes worst-tick load (correct for MD billing) |
| Planner reasons about 800 kW even when state differs | Planner uses state value, no anchor |
| CBC timeout → 0 kW dispatch silently | Timeout → fallback_discharge path with log |
| MD override in controller capped at 100 kW | MD override capped at max_discharge_kw |
