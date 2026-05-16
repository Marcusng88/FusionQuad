# FusionQuad — Domain Glossary

Use these terms exactly. Consistent language matters.

---

## Core Domain

**BESS** — Battery Energy Storage System. Physical battery + inverter. Charges/discharges on command.

**Peak Shaving** — Reducing grid import below MD limit by discharging BESS during high-load periods.

**MD Limit (Maximum Demand)** — Contractual cap on peak kW import from grid. Exceeding triggers demand charge (RM/kW/month).

**Demand Charge** — Monthly penalty for peak demand. Billed on highest 30-min interval in month. Primary cost driver.

**Tariff Window** — Classification of current 30-min interval: `PEAK` (weekday 14:00–22:00), `OFF_PEAK`, or `WEEKEND` (weekends + holidays).

**Dispatch Action** — Command to BESS: `discharge`, `charge`, or `hold`.

**Dispatch Result** — Outcome of executing dispatch action: new SOC, temperature delta, cycle count delta.

**SOC (State of Charge)** — Battery charge level 0.0–1.0 (0%–100%).

**Interval** — 30-minute simulation timestep. 48 per full day.

**Tick** — Synonym for interval in simulation context.

---

## Agents

**Forecaster** — ML module (GRU). Consumes historical load actuals, predicts next 6 intervals.

**Planner** — Deep Agent. Selects dispatch strategy using RAG over strategies/ and experience/.

**Controller** — Deep Agent. Executes dispatch. Calls MILP solver as tool.

**Auditor** — Deep Agent. Evaluates each tick. Writes experience report at end of day.

**Tariff Node** — Config module (not an agent). Computes TariffContext from current_time.

---

## State Concepts

**BatteryState** — `{ soc, capacity_kwh, cycle_count, temperature_c }`. Owned by Controller.

**ForecastResult** — `{ load_forecast, confidence, horizon }`. Produced by Forecaster.

**TariffContext** — `{ window, energy_rate, demand_charge, tariff_type }`. Produced by Tariff Node. Single source of truth for rates.

**OptimizationStrategy** — `{ strategy_name, shave_kw, reserve_soc_pct, target_soc_end, rationale, confidence, md_limit_kw }`. Produced by Planner. Consumed by Controller.

**DispatchAction** — `{ action, discharge_kw, charge_kw, duration_min, expected_soc_after }`. Produced by MILP solver. Consumed by Controller.

**DispatchResult** — `{ new_soc, temp_increase_c, cycle_count_delta, action_taken }`. Produced by mock inverter.

---

## Knowledge Sources (RAG)

**strategies/** — Static dispatch guidelines (.md). Planner reads.

**experience/** — Auditor-written post-day reports (.md). Planner reads. Auditor writes.

**tariff/** — TNB rate card (.md). Planner reads.

---

## Metrics

**Delta Score** — Per-tick performance 0–100. 60% shave score + 40% forecast accuracy.

**Shave %** — `(shaved_kw / possible_shave_kw) * 100`. Day-level metric.

**Compliance Rate** — `within_limit_ticks / total_ticks`. % ticks below MD limit.

**Interval Savings (RM)** — `shave_kw * (duration_min / 60) * energy_rate`.

---

## Infrastructure

**Simulation Session** — Single run instance. Has session_id, day_type, tick state, log path.

**Simulation Window** — User-selected tick range within available CSV data. Default: highest-breach 48-tick window.

**MILP Solver** — Mixed-integer linear program (PuLP + CBC). Minimizes energy cost subject to SOC/power/MD constraints.

**Experience Loop** — Auditor writes day report -> Planner reads next day -> strategy improves.
