# Agent Spec: Optimization

## Purpose

Generate the optimal BESS dispatch schedule using Mixed-Integer Linear Programming (MILP). Receives `optimization_strategy` from Planner and `load_forecast` from Forecasting, produces `dispatch_plan` for Controller.

## Type

**Custom node** (not a Deep Agent) — MILP solver is deterministic, not an LLM agent.

## Position in Pipeline

```
[Planner] → [Optimization] → [Controller] → [Auditor]
```

Optimization runs **every simulation tick** after Planner produces strategy.

---

## Input (from AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `state.optimization_strategy` | `dict` | Strategy dict from Planner |
| `state.load_forecast` | `dict[str, list[float]]` | Forecasted kW values |
| `state.tariff_window` | `str` | "PEAK" | "OFF_PEAK" | "WEEKEND" |
| `state.battery_soc` | `float` | Current BESS SOC 0–1 |
| `state.bess_capacity_kwh` | `float` | Total BESS capacity (e.g., 500) |
| `state.md_limit_kw` | `float` | Maximum demand threshold (default 800) |
| `state.current_dispatch_index` | `int` | Which interval in dispatch_plan to execute next |

---

## Output (written to AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `dispatch_plan` | `list[dict]` | Full schedule for current day |
| `current_dispatch_index` | `int` | Index of next action to execute |
| `dispatch_action` | `dict` | The current tick's action (extracted for Controller) |

```python
# dispatch_plan entry:
{
    "interval": int,              # 0-47 (30-min intervals in a day)
    "action": "discharge" | "charge" | "hold",
    "discharge_kw": float | None, # kW for this interval
    "charge_kw": float | None,    # kW to charge (during OFF_PEAK)
    "target_soc": float | None,    # SOC expected after this interval
    "expected_savings_rm": float,  # estimated RM saved this interval
}

# dispatch_action (current tick):
{
    "action": "discharge",
    "discharge_kw": 80,
    "duration_min": 30,
    "expected_soc_after": 0.57,
}
```

---

## MILP Model (PuLP)

```python
# Decision Variables
P = pulp.LpVariable("power_kw", -max_charge_kw, max_discharge_kw)  # positive=discharge
S = pulp.LpVariable("soc", 0.20, 0.95)  # state-of-charge

# Objective: minimize energy_cost + demand_penalty
# minimize Σ (energy_rate * P * dt / 3600) + demand_charge * max(0, load_forecast[t] - P - md_limit_kw)

# Constraints
1. Power bounds: P <= max_discharge_kw (100kW), P >= -max_charge_kw (-50kW)
2. SOC dynamics: soc[t+1] = soc[t] - (P * dt) / (bess_capacity_kwh * 3600)
3. MD threshold: load_forecast[t] - P <= md_limit_kw
4. SOC limits: 0.20 <= soc[t] <= 0.95
5. Strategy constraints from optimization_strategy (e.g., reserve_soc_pct)
```

---

## Tools

| Tool | Purpose |
|------|---------|
| `PuLP solver` | MILP optimization — minimize cost subject to constraints |
| `warm_start` | Use previous tick's solution as starting point |

**Solver settings:**
- Max solve time: 1 second
- Solver: `PuLP.PULP_CBC_CMD(msg=0)`
- Warm-start from previous dispatch_plan if available

---

## Logic

```
1. Receive optimization_strategy from Planner
2. Extract targets/constraints: shave_kw, reserve_soc_pct, strategy constraints
3. Receive load_forecast (list of kW values for future intervals)
4. Build MILP model:
   - Variables: power_kw per interval, soc per interval
   - Objective: minimize energy_cost + demand_penalty
   - Constraints: SOC bounds, power bounds, MD threshold, strategy rules
5. Solve MILP → dispatch_plan
6. Extract dispatch_action for current tick (index = current_dispatch_index)
7. Return {dispatch_plan, current_dispatch_index, dispatch_action}
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| MILP solve time > 1 second | Abort solve, use fallback: discharge at `shave_kw` from strategy |
| Empty load_forecast | Return empty dispatch_plan, log warning |
| battery_soc < 0.20 | Force "hold" action — BESS too low to discharge |
| Optimization strategy missing | Fall back to "conservative" — 50kW discharge if SOC > 30% |
| No feasible solution | Return "hold" action, log "infeasible — constraints too tight" |

---

## Acceptance Criteria

- [ ] MILP solver produces dispatch_plan for all intervals
- [ ] SOC never goes below 20% or above 95%
- [ ] Discharge never exceeds 100kW per 30-min interval
- [ ] `dispatch_action` is set for current tick
- [ ] Warm-start from previous solution (reduces solve time)
- [ ] Falls back to hold/discharge if solve fails
- [ ] Solve completes within 1 second

---

## Dependencies

- Reads: `state.optimization_strategy`, `state.load_forecast`, `state.battery_soc`, `state.bess_capacity_kwh`, `state.current_dispatch_index`
- Writes: `state.dispatch_plan`, `state.current_dispatch_index`, `state.dispatch_action`
- Python packages: `puLP`

---

## File Location

```
backend/app/agents/optimization.py   # node implementation
```
