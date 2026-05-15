# Agent Spec: Controller (Deep Agent)

## Purpose

Execute the BESS dispatch action via a mock inverter tool. Observes the SoC response (drain, temperature, cycle count) and writes results to state for the Auditor to evaluate. This closes the perceive→act loop in the simulation.

## Type

**Deep Agent** (`create_deep_agent`) — ReAct loop with custom mock_inverter tool.

## Position in Pipeline

```
[Optimization] → [Controller] → [Auditor]
```

Controller runs **every simulation tick** after Optimization produces dispatch_action.

---

## Input (from AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `state.dispatch_action` | `dict` | `{action, discharge_kw, duration_min, expected_soc_after}` |
| `state.battery_soc` | `float` | Current SOC before dispatch |
| `state.cycle_count` | `float` | Current accumulated cycle count |
| `state.current_time` | `datetime` | Simulation time |

---

## Output (written to AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `dispatch_result` | `dict` | Inverter response: new_soc, temp_increase, cycle_increment |
| `battery_soc` | `float` | Updated SOC after dispatch |
| `cycle_count` | `float` | Updated accumulated cycle count |
| `temperature_c` | `float` | BESS temperature estimate |

```python
# dispatch_result schema:
{
    "new_soc": float,                 # SOC after dispatch (0-1)
    "temp_increase_c": float,         # temperature rise from this dispatch
    "cycle_count_increment": float,   # fraction of a cycle (0.01 = 1% of cycle)
    "action_taken": str,             # "discharge" | "charge" | "hold"
    "actual_discharge_kw": float,     # actual kW dispatched
    "efficiency_loss_pct": float,     # round-trip efficiency loss (default 5%)
}
```

---

## Tools

### Primary Tool: mock_inverter_dispatch

```python
@tool
def mock_inverter_dispatch(
    action: str,              # "discharge" | "charge" | "hold"
    power_kw: float,          # kW to discharge or charge
    duration_min: int,        # duration in minutes (always 30)
    current_soc: float,       # SOC before dispatch
    bess_capacity_kwh: float,  # total BESS capacity
    temperature_c: float,    # current BESS temperature
) -> dict:
    """Mock smart inverter dispatch — simulates BESS response."""
```

**Logic:**
```python
if action == "discharge":
    energy_kwh = power_kw * (duration_min / 60)
    soc_delta = energy_kwh / bess_capacity_kwh
    efficiency_loss = 0.05  # 5% round-trip loss
    actual_discharge = energy_kwh * (1 - efficiency_loss)
    new_soc = current_soc - (actual_discharge / bess_capacity_kwh)
    temp_increase = 0.5 * (power_kw / 100)  # scales with power
    cycle_increment = (energy_kwh / bess_capacity_kwh)

elif action == "charge":
    energy_kwh = power_kw * (duration_min / 60)
    soc_delta = energy_kwh / bess_capacity_kwh
    new_soc = min(current_soc + soc_delta, 0.95)  # cap at 95%
    temp_increase = 0.2 * (power_kw / 100)
    cycle_increment = -0.005  # charging counts as negative cycle

else:  # hold
    new_soc = current_soc
    temp_increase = 0.1  # passive temperature rise
    cycle_increment = 0.0
```

### Built-in Deep Agent Tools

- `write_todos` — log dispatch steps to decision trail
- `read_file` — read dispatch history if needed

---

## ReAct Loop

```
Perceive:
  → "dispatch_action: discharge 80kW for 30min. Current SOC: 65%. Expected SOC after: 57%."
Reason:
  → "This is within limits. SOC 65% > 20% minimum. Check if power exceeds inverter limit."
Act:
  → mock_inverter_dispatch(action="discharge", power_kw=80, duration_min=30,
                           current_soc=0.65, bess_capacity_kwh=500, temperature_c=32)
Observe:
  → {new_soc: 0.57, temp_increase_c: 0.4, cycle_count_increment: 0.016, action_taken: "discharge"}
Reason:
  → "SOC dropped from 65% to 57% as expected. 16% of a cycle used. Temperature rise 0.4°C."
Act:
  → write dispatch_result to state
  → advance current_dispatch_index++
```

---

## System Prompt

```
You are the Controller Agent for FusionQuad — you execute BESS dispatch actions.

Your task:
1. Read the current dispatch_action from state
2. Call mock_inverter_dispatch with correct parameters
3. Observe the response (new_soc, temp, cycle_count)
4. Write dispatch_result to state
5. Log the action using write_todos for the AI reasoning trace

State fields you manage:
- battery_soc: updated to dispatch_result.new_soc
- cycle_count: incremented by dispatch_result.cycle_count_increment
- temperature_c: incremented by dispatch_result.temp_increase_c

Safety rules:
- If dispatch_action is None or "hold", do not call inverter — just log "hold"
- If battery_soc < 0.20 before dispatch, call "hold" instead and log "SOC too low — preserving"
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| `dispatch_action` is None | Log "no action scheduled", write empty dispatch_result |
| `dispatch_action.action == "hold"` | Don't call inverter — new_soc = current_soc, temp_increase = 0.1 |
| SOC < 0.20 before dispatch | Force "hold", log "SOC critically low — preserved" |
| power_kw = 0 | Treat as "hold" |
| `bess_capacity_kwh` not in state | Default to 500 kWh, log warning |

---

## Acceptance Criteria

- [ ] Deep Agent with mock_inverter_dispatch tool registered
- [ ] ReAct loop runs once per simulation tick (perceive → act → observe → write)
- [ ] `dispatch_result` written to state with all required fields
- [ ] `battery_soc` updated to new_soc after each dispatch
- [ ] `cycle_count` incremented (or decremented for charging)
- [ ] `temperature_c` updated (accumulates through the day)
- [ ] Falls back to "hold" when SOC is critically low
- [ ] `write_todos` logs dispatch steps for AI reasoning trace

---

## Dependencies

- Reads: `state.dispatch_action`, `state.battery_soc`, `state.cycle_count`, `state.bess_capacity_kwh`, `state.temperature_c`
- Writes: `state.dispatch_result`, `state.battery_soc`, `state.cycle_count`, `state.temperature_c`, `state.last_dispatch_kw`, `state.last_dispatch_duration_min`

---

## File Location

```
backend/app/agents/controller.py   # Deep Agent wrapper node
```
