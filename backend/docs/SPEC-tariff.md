# Agent Spec: Tariff

## Purpose

Compute the current TNB tariff window and applicable energy/demand rates from the simulation datetime. Provides pricing context to Planner (for strategy) and Optimization (for cost calculation).

## Type

**Custom node** (not a Deep Agent) — pure datetime → tariff computation. No LLM reasoning.

## Position in Pipeline

```
[DataLoader] → [Forecasting] → [Tariff] → [Planner] → ...
```

Tariff runs **every simulation tick** (same as Forecasting).

---

## Input

| Source | Description |
|--------|-------------|
| `state.current_time` | `datetime` — current simulation time |

---

## Output

Written to `AgentState`:

| Key | Type | Description |
|-----|------|-------------|
| `tariff_window` | `str` | "PEAK" | "OFF_PEAK" | "WEEKEND" |
| `energy_rate` | `float` | sen/kWh for current window |
| `demand_charge` | `float` | RM/kW — 0 if off-peak/weekend |
| `tariff_type` | `str` | "C2" | "E2" | "C1" | "E1" (default C2) |

---

## State Schema (partial)

```python
class AgentState(TypedDict):
    tariff_window: str | None       # "PEAK" | "OFF_PEAK" | "WEEKEND"
    energy_rate: float | None        # sen/kWh
    demand_charge: float | None     # RM/kW
    tariff_type: str | None         # "C2" | "E2" | "C1" | "E1"
    current_time: datetime | None
```

---

## Logic

```
1. Receive current_time from state
2. Determine tariff_window:
     if current_time.weekday >= 5:           → "WEEKEND"
     elif 14 <= current_time.hour < 22:      → "PEAK"    (2PM–10PM weekdays)
     else:                                    → "OFF_PEAK"
3. Select tariff_type (default C2 — MV Commercial TOU)
4. Look up rates from TARIFF_RATES:

   TARIFF_RATES[C2]:
     peak_energy: 28.52 sen/kWh
     off_peak_energy: 24.43 sen/kWh
     capacity: 30.19 RM/kW
     network: 66.87 RM/kW
     → total_demand = 97.06 RM/kW

   DEMAND_RATES[C2]: 97.06 RM/kW
   (for C2/E2 = 97.06, C1/E1 = 89.27)

5. Set energy_rate and demand_charge:
     PEAK     → energy_rate = peak_energy, demand_charge = total_demand
     WEEKEND  → energy_rate = off_peak_energy, demand_charge = 0
     OFF_PEAK → energy_rate = off_peak_energy, demand_charge = 0
```

---

## TNB Tariff Rates (July 2025)

| Tariff | Peak Energy (sen/kWh) | Off-Peak Energy (sen/kWh) | Capacity (RM/kW) | Network (RM/kW) | Total MD (RM/kW) |
|--------|----------------------|---------------------------|-----------------|-----------------|-----------------|
| C2     | 28.52 | 24.43 | 30.19 | 66.87 | 97.06 |
| E2     | 28.52 | 22.40 | 30.19 | 66.87 | 97.06 |
| C1     | 28.52 | 24.43 | 29.43 | 59.84 | 89.27 |
| E1     | 28.52 | 22.40 | 29.43 | 59.84 | 89.27 |

**Critical rule**: MD charges (demand_charge) **do not apply** during OFF_PEAK or WEEKEND for MV/HV customers. Set to 0 in those windows.

---

## Tools

| Tool | Purpose |
|------|---------|
| `TARIFF_RATES` dict | Lookup energy rates by tariff type + window |
| `DEMAND_RATES` dict | Lookup demand charge by tariff type |
| `_get_tariff_window(datetime) → str` | Pure function: weekday/hour → window name |

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| datetime is None | Default to PEAK + log warning |
| Unknown tariff_type | Default to "C2" |
| Weekend + PEAK hour (impossible) | WEEKEND takes precedence — tariff_window = "WEEKEND" |
| Public holiday | Treat as WEEKEND — check via holiday calendar |

**Holiday handling**: If `current_time` matches a Malaysian public holiday (from `backend/data/holidays.json`), treat as WEEKEND regardless of weekday.

---

## Acceptance Criteria

- [ ] Correct window classification: weekday 2PM–10PM = PEAK, weekday 10PM–2PM = OFF_PEAK, Sat/Sun/Holiday = WEEKEND
- [ ] energy_rate matches the tariff table above
- [ ] demand_charge = 0 during OFF_PEAK and WEEKEND (critical rule)
- [ ] Runs every tick (not once)
- [ ] No LLM — pure computation from datetime

---

## Dependencies

- Reads: `state.current_time`
- Writes: `state.tariff_window`, `state.energy_rate`, `state.demand_charge`, `state.tariff_type`

---

## File Location

```
backend/app/agents/tariff.py        # node implementation (replace existing)
backend/data/holidays.json          # Malaysian public holiday list (to add)
```