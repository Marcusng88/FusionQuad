# Agent Spec: Planner (Deep Agent)

## Purpose

High-level strategy agent that reads RAG-backed guideline files and sets the `optimization_strategy` dict consumed by the Controller (via MILP tool). Analyzes forecast context, day type, tariff window, and BESS state to produce a situational strategy with rationale.

## Type

**Deep Agent** (`create_deep_agent`) — full ReAct loop with SkillsMiddleware for RAG.

## Position in Pipeline

```
[Forecasting] → [Tariff] → [Planner] → [Controller] → [Auditor]
```

Planner runs **every simulation tick** after Tariff, before Controller (MILP).

---

## Input (from AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `state.load_forecast` | `dict[str, list[float]]` | Next interval predictions in kW |
| `state.forecast_confidence` | `dict[str, float]` | Model confidence 0–1 |
| `state.tariff_window` | `str` | "PEAK" | "OFF_PEAK" | "WEEKEND" |
| `state.day_type` | `str` | "weekday" | "holiday" | "solar_duck_curve" |
| `state.battery_soc` | `float` | Current BESS state-of-charge 0–1 |
| `state.bess_capacity_kwh` | `float` | Total BESS capacity |
| `state.current_time` | `datetime` | Simulation time |
| `state.cycle_count` | `float` | Accumulated BESS cycle count |

---

## Output (written to AgentState)

| Key | Type | Description |
|-----|------|-------------|
| `optimization_strategy` | `dict` | Strategy dict (see below) |

```python
# optimization_strategy schema:
{
    "strategy_name": str,           # e.g., "aggressive_peak_shaving"
    "targets": {
        "shave_kw": float,           # target peak reduction kW
        "reserve_soc_pct": float,    # minimum SOC reserve %
    },
    "constraints": list[str],        # e.g., ["no_discharge_before_2PM", "max_100kW_interval"]
    "rationale": str,                # human-readable reasoning
    "md_limit_kw": float,            # from state.md_limit_kw
    "confidence": float,             # from forecast_confidence
}
```

---

## Tools (RAG + Context)

| Tool | Description |
|------|-------------|
| `search_guidelines(query: str) → list[dict]` | Semantic search over `./strategies/*.md` — returns ranked fragments with relevance scores |
| `read_guideline_file(path: str) → str` | Read full content of one strategy file |
| `get_forecast_context() → str` | Construct formatted string of forecast + confidence + tariff window |

**Built-in Deep Agent tools** (always available):
- `ls` — list strategy directory
- `read_file` — read specific guideline file
- `write_todos` — plan sub-tasks
- `grep` — search file content

---

## Skills (RAG Source)

```
backend/strategies/
├── aggressive_peak_shaving.md   # weekday PEAK strategy
├── holiday_surge.md              # high-load holiday strategy
├── solar_duck_curve.md           # post-solar duck curve strategy
├── offpeak_valley_fill.md        # charging strategy during OFF_PEAK
├── general_bess_guidelines.md    # SOC limits, cycle count thresholds
└── SKILL.md                      # required by Deep Agents SkillsMiddleware

backend/experience/
├── 2025-09-01-solar_duck_curve.md  # historical audit entries (Planner reads this too)
└── ...
```

---

## ReAct Loop

```
Perceive:
  → "Current state: forecast={load_forecast}, tariff={tariff_window}, day_type={day_type}, SOC={battery_soc}"
Reason:
  → "What strategy applies? Check which guideline matches tariff_window + day_type + forecast profile"
Act:
  → search_guidelines(f"peak shaving {tariff_window} {day_type}")
  → read_guideline_file(highest_relevance_result.path)
  → get_forecast_context()
Reason:
  → "Based on guideline + forecast context, which strategy rules apply?"
Act:
  → Write optimization_strategy to state
  → Include: strategy_name, targets, constraints, rationale
```

---

## System Prompt

```
You are the Planner Agent for FusionQuad — an AI-powered BESS peak shaving system.
Your role: Given the current forecast, tariff window, day type, and BESS state,
          select the appropriate dispatch strategy from the guidelines.

Context you receive:
- load_forecast: predicted kW for next interval
- forecast_confidence: model confidence (0–1)
- tariff_window: PEAK | OFF_PEAK | WEEKEND
- day_type: weekday | holiday | solar_duck_curve
- battery_soc: current state-of-charge (0–1)
- cycle_count: total BESS cycles

Task:
1. Search guidelines for strategy matching tariff_window + day_type
2. Read the most relevant guideline
3. Apply strategy rules given current BESS state and forecast
4. Output optimization_strategy dict

Output format:
{
  "strategy_name": "...",
  "targets": {"shave_kw": ..., "reserve_soc_pct": ...},
  "constraints": [...],
  "rationale": "...",
  "md_limit_kw": ...,
  "confidence": ...
}
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No matching guideline found | Default to "conservative_shaving": 50% max discharge, 30% SOC reserve |
| SOC < 20% | Force "preserve_mode": no discharge, log warning |
| forecast_confidence < 0.5 | Reduce shave target by 25%, add confidence warning to rationale |
| No forecast data | Default to "hold" strategy — no dispatch, wait for data |

---

## Acceptance Criteria

- [ ] Deep Agent initialized with `FilesystemBackend` + `SkillsMiddleware`
- [ ] Strategy files in `./strategies/` are loaded via skills
- [ ] `search_guidelines` + `read_guideline_file` tools work
- [ ] `optimization_strategy` written to state every tick
- [ ] Planner runs after Forecasting + Tariff, before Optimization
- [ ] Falls back to conservative default when no guideline matches
- [ ] Teammates can add new strategy .md files without code changes

---

## Dependencies

- Reads: `state.load_forecast`, `state.forecast_confidence`, `state.tariff_window`, `state.day_type`, `state.battery_soc`, `state.bess_capacity_kwh`, `state.current_time`, `state.cycle_count`
- Writes: `state.optimization_strategy`
- Skills: `backend/strategies/*.md`

---

## File Location

```
backend/app/agents/planner.py              # Deep Agent wrapper node
backend/strategies/                        # RAG guideline files (teammates edit)
    aggressive_peak_shaving.md
    holiday_surge.md
    solar_duck_curve.md
    offpeak_valley_fill.md
    general_bess_guidelines.md
    SKILL.md
backend/experience/                       # RAG historical audit files (Planner + Auditor read)
```
