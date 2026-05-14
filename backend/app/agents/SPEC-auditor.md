# Agent Spec: Auditor (Deep Agent)

## Purpose

Post-dispatch verification agent that evaluates Controller action quality using three modes: delta scoring (numeric), rule-based safety checks, and LLM reasoning. Accumulates `decision_log` across all ticks.

## Type

**Deep Agent** (`create_deep_agent`) — ReAct loop with three evaluation tool modes.

## Position in Pipeline

```
[Controller] → [Auditor] → [END]
```

---

## Input (from AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `state.dispatch_result` | `dict` | `{new_soc, temp_increase_c, cycle_count_increment, action_taken}` |
| `state.dispatch_action` | `dict` | `{action, discharge_kw, duration_min}` |
| `state.baseline_load` | `float` | Original load kW before BESS dispatch |
| `state.actual_load` | `float` | Load after dispatch |
| `state.battery_soc` | `float` | SOC after dispatch |
| `state.cycle_count` | `float` | Updated cycle count |
| `state.tariff_window` | `str` | "PEAK" \| "OFF_PEAK" \| "WEEKEND" |
| `state.current_time` | `datetime` | Simulation time |
| `state.decision_log` | `list[dict]` | Accumulated history |
| `state.md_limit_kw` | `float` | 800 kW default |

---

## Output (written to AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `auditor_result` | `dict` | Latest evaluation result |
| `decision_log` | `list[dict]` | Full Perceive→Reason→Act→Evaluate history |
| `shave_percentage` | `float` | Peak reduction % for hero KPIs |
| `total_savings_rm` | `float` | Cumulative RM saved |
| `within_limit_ticks` | `int` | Count of intervals within MD limit |

---

## Evaluation Tools (3 Modes)

### Mode 1: evaluate_delta
Numeric scoring — shave_kw, shave_pct, forecast_error_pct, interval_savings_rm.

### Mode 2: evaluate_rules
Safety checks — SOC < 20%, cycle_count > 3000, temp_increase > 5C, discharge > 100kW, OFF_PEAK discharge.

### Mode 3: evaluate_llm
LLM reasoning for complex cases (delta_score < 50 OR forecast_error > 20% OR violations).

---

## Evaluation Order

1. **evaluate_rules FIRST** — safety is non-negotiable
2. **evaluate_delta SECOND** — numeric scoring always
3. **evaluate_llm ONLY when**: delta_score < 50 OR forecast_error > 20% OR rule violations

---

## decision_log Entry Format

```
{
  "timestamp": "2025-07-15 14:00",
  "interval": 28,
  "perceive": "Grid import 920kW — exceeds 800kW MD limit by 120kW",
  "reason": "BESS SoC at 65%, sufficient for 80kW discharge",
  "act": "Dispatch 80kW for 30min → SOC drops to 57%",
  "evaluate": { auditor_result for this tick }
}
```

---

## End-of-Day Summary

```
{
  "total_intervals": 48,
  "within_limit_ticks": 42,
  "compliance_rate": 0.875,
  "total_savings_rm": ...,
  "peak_shave_pct": ...,
  "avg_soc": ...,
  "max_temp_c": ...,
  "total_cycles_used": ...,
  "critical_violations": [...],
  "recommendation": str,
}
```

---

## Acceptance Criteria

- [ ] Deep Agent with 3 evaluation tools registered
- [ ] evaluate_rules runs first (safety) on every tick
- [ ] evaluate_delta runs on every tick
- [ ] evaluate_llm runs only for complex cases
- [ ] decision_log entry created every tick
- [ ] total_savings_rm accumulates across all ticks
- [ ] Auditor result schema matches dashboard consumption

---

## File Location

```
backend/app/agents/auditor.py
```