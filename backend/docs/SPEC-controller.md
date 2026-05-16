# Agent Spec: Controller (Deep Agent with MILP Tool)

## Purpose

Execute BESS dispatch actions by calling the MILP optimizer tool and then executing via mock inverter. The Controller is the end of the per-tick planning loop — it receives the `optimization_strategy` from Planner and produces `dispatch_result` for the Auditor.

## Type

**Deep Agent** (`create_deep_agent`) — ReAct loop with `milp_optimizer` + `mock_inverter_dispatch` tools.

## Position in Pipeline

```
[Planner] → [Controller] → [Auditor]
```

Controller runs **every simulation tick** after Planner produces `optimization_strategy`.

---

## Input (from AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `state.optimization_strategy` | `dict` | Planner's strategy dict |
| `state.load_forecast` | `dict[str, list[float]]` | Forecast kW values |
| `state.battery_soc` | `float` | Current SOC before dispatch |
| `state.bess_capacity_kwh` | `float` | Total BESS capacity |
| `state.tariff_window` | `str` | PEAK / OFF_PEAK / WEEKEND |
| `state.md_limit_kw` | `float` | Maximum demand limit |
| `state.temperature_c` | `float` | Current BESS temperature |
| `state.cycle_count` | `float` | Current accumulated cycle count |
| `state.baseline_load` | `float` | Raw grid import for this tick |

---

## Output (written to AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `dispatch_action` | `dict` | `{action, discharge_kw, charge_kw, duration_min, expected_soc_after}` |
| `dispatch_result` | `dict` | Inverter response: new_soc, temp_increase, cycle_increment |
| `battery_soc` | `float` | Updated SOC after dispatch |
| `cycle_count` | `float` | Updated accumulated cycle count |
| `temperature_c` | `float` | BESS temperature estimate |
| `last_dispatch_kw` | `float` | Actual kW dispatched |
| `actual_load` | `float` | Grid import after BESS action |

---

## Tools

### Tool 1: `milp_optimizer`

```python
@tool
def milp_optimizer(
    load_forecast: list[float],
    tariff_window: str,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    optimization_strategy: dict,
    previous_dispatch_plan: list[dict] | None = None,
) -> dict:
    """MILP solver — computes optimal BESS dispatch for this tick."""
```

**Logic**: Passes to `OptimizationSolver.solve()` with the current tick's forecast and planner's strategy. Returns `dispatch_action` for the current interval only.

### Tool 2: `mock_inverter_dispatch`

```python
@tool
def mock_inverter_dispatch(
    action: str,
    power_kw: float,
    duration_min: int,
    current_soc: float,
    bess_capacity_kwh: float,
    temperature_c: float,
) -> dict:
    """Mock smart inverter dispatch — simulates BESS response."""
```

**Logic**:
```python
if action == "discharge":
    energy_kwh = power_kw * (duration_min / 60)
    actual_discharge = energy_kwh * (1 - 0.05)  # 5% round-trip loss
    new_soc = current_soc - (actual_discharge / bess_capacity_kwh)
    temp_increase = 0.5 * (power_kw / 100)
elif action == "charge":
    energy_kwh = power_kw * (duration_min / 60)
    new_soc = min(current_soc + (energy_kwh / bess_capacity_kwh), 0.95)
    temp_increase = 0.2 * (power_kw / 100)
else:
    new_soc = current_soc
    temp_increase = 0.1
```

---

## ReAct Loop

```
Perceive:
  → "Planner set optimization_strategy: aggressive_peak_shaving. Forecast 820kW. SOC 65%."
Reason:
  → "MILP needs to find optimal discharge given forecast + SOC constraints. Then execute via inverter."
Act:
  → milp_optimizer(load_forecast=[820], tariff_window="PEAK", battery_soc=0.65, ...)
Observe:
  → {dispatch_action: {action: "discharge", discharge_kw: 80, duration_min: 30}}
Act:
  → mock_inverter_dispatch(action="discharge", power_kw=80, current_soc=0.65, ...)
Observe:
  → {new_soc: 0.57, temp_increase_c: 0.4, cycle_count_increment: 0.016}
Act:
  → Return dispatch_result + updated battery state
```

---

## System Prompt

```
You are the Controller Agent for FusionQuad — you execute BESS dispatch actions using MILP optimization.

Your workflow per tick:
1. Read optimization_strategy from state (set by Planner)
2. Call milp_optimizer with current state parameters to get dispatch_action
3. Execute dispatch via mock_inverter_dispatch
4. Observe the response (new_soc, temp, cycle_count)
5. Return dispatch_result and updated battery state

Never call mock_inverter_dispatch before milp_optimizer for the same tick.
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| SOC < 20% before dispatch | Force action="hold", skip milp_optimizer |
| milp_optimizer returns null | Use local `_local_milp_fallback()` computation |
| agent invocation fails | Fall back to local MILP computation + local inverter dispatch |
| tariff_window unknown | Default to OFF_PEAK rates |

---

## Acceptance Criteria

- [ ] `milp_optimizer` tool registered with Deep Agent
- [ ] `mock_inverter_dispatch` tool registered with Deep Agent
- [ ] ReAct loop: milp_optimizer → mock_inverter_dispatch → observe → write state
- [ ] `dispatch_result` written to state with all required fields
- [ ] `battery_soc` updated to new_soc after each dispatch
- [ ] `cycle_count` incremented (or decremented for charging)
- [ ] `temperature_c` accumulates through the day
- [ ] SOC < 20% triggers forced "hold"
- [ ] Local fallback if deep agent invocation fails

---

## Dependencies

- Reads: `state.optimization_strategy`, `state.load_forecast`, `state.battery_soc`, `state.bess_capacity_kwh`, `state.tariff_window`, `state.md_limit_kw`, `state.temperature_c`, `state.baseline_load`
- Writes: `state.dispatch_action`, `state.dispatch_result`, `state.battery_soc`, `state.cycle_count`, `state.temperature_c`, `state.last_dispatch_kw`, `state.last_dispatch_duration_min`, `state.actual_load`