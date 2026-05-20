# FusionQuad — System Flaw Report & Harness-Engineering Analysis

**Scope:** the whole simulation system + the entire LangGraph flow (`data_loader → forecast ∥ tariff → planner → controller → auditor`) + the simulation service + supporting code.
**Audience:** developers. This is a punch-list and an architecture review, not a polished report.
**Evidence base:** full code read; `backend/app/logs/2025-04-07-weekday.json`; `backend/experience/2025-04-07-weekday.md`; `problem_statement.md`; LangChain / LangGraph / deepagents documentation; 2026 harness-engineering literature (see References).

---

## Table of contents

1. How the pipeline runs (per tick)
2. Harness-engineering assessment — the correct way, and where FusionQuad diverges
3. Architecture-level findings
4. Flaws — Critical
5. Flaws — High
6. Flaws — Medium
7. Minor issues
8. Target architecture (the corrected harness)
9. Recommended fix sequence
10. References

Each flaw block: **Symptom · Root cause (file:line) · Fix · Effort (S/M/L) · Verify**. Stage tag in `[brackets]`.

---

## 1. How the pipeline runs (per 30-min tick)

`SimulationService.step()` / `run_stream()` re-invokes the full compiled LangGraph workflow once per simulation tick:

```
START → data_loader → forecast ─┐
                                ├→ planner → controller → auditor → END
                    → tariff ───┘
```

- **data_loader** — re-reads the facility CSV from disk and rebuilds a record list (every tick).
- **forecast** — GRU / GRU-attention PyTorch model; `predict_horizon` from history ending at `current_record_index`.
- **tariff** — wall clock → `PEAK` / `OFF_PEAK` / `WEEKEND`.
- **planner** — `deepagents` LLM agent. Reads `/strategies/` + `/experience/` via a `CompositeBackend`; emits an `OptimizationStrategy` (`shave_kw`, `target_soc_end`, `reserve_soc_pct`, …).
- **controller** — `deepagents` LLM agent. Calls the `milp_optimizer` tool (PuLP MILP); returns a `DispatchAction`; a mock inverter applies it.
- **auditor** — deterministic rule + delta scoring, optional LLM review; writes `planner_feedback` for the next tick; at end-of-day an LLM writes an `/experience/` markdown file.

**Observed result (weekday log, 11 ticks):** 3/11 PEAK ticks within the MD limit (27% compliance). Battery discharge pinned at ~43–45 kW on *every* PEAK tick regardless of a planner `shave_kw` ranging 125–285 kW. Reported total savings RM 56.97.

---

## 2. Harness-engineering assessment — the correct way, and where FusionQuad diverges

### 2.1 What an agent harness is supposed to do

LangChain's own documentation calls `deepagents` **"an agent harness"** and defines a harness by four context duties:

> *Input context* — system prompt, memory, skills, tool prompts shape what the agent knows at startup.
> *Compression* — built-in offloading and summarization keep context within window limits as the task progresses.
> *Isolation* — subagents quarantine heavy work and return only results.
> *Long-term memory* — persistent storage across threads via the virtual filesystem.

LangGraph documentation draws the line that matters most here:

> *Workflows have predetermined code paths and are designed to operate in a certain order. Agents are dynamic and define their own processes and tool usage.*

2026 harness-engineering literature adds the failure taxonomy: roughly **65% of agent failures are harness defects**, not model defects — and they cluster into three classes: **context drift**, **schema misalignment**, and **state degradation**. The corrective principles are consistent across sources:

- The LLM is a *non-deterministic reasoner that proposes actions*; surrounding code is the *deterministic layer that validates and executes them*.
- **Offload precision work** — arithmetic, date logic, structured-data retrieval — to deterministic tools. Never let the model compute a number you can compute exactly.
- Expose a **small, job-specific tool surface** with explicit schemas and structured (deterministic) outputs.
- **Single-responsibility agents**: one agent, one decision it is genuinely qualified to make.
- Use **context resets and structured handoff artifacts** between phases; do not let one long thread accumulate forever.

### 2.2 FusionQuad against the harness scorecard

| Harness duty | Correct practice | FusionQuad today | Defect class | Flaw |
|---|---|---|---|---|
| Input context | Prompts/skills/strategy files externalized and consistent with the filesystem | Prompts externalized as `.md` (good) — but the planner prompt references 5 strategy files; only 1 exists | schema misalignment | F10 |
| Compression / offloading | Use built-in summarization/offloading for long sessions | Per-*session* thread, **no summarization** → context grows unbounded across 48 ticks | state degradation | F7 |
| Isolation (subagents) | Delegate heavy/ancillary work to subagents; return compressed results | Not used at all; 3 sibling top-level agents, no `task`-tool delegation | — | §3, F18 |
| Long-term memory | Persistent cross-run notes via the virtual filesystem | `/experience/` files via `FilesystemBackend` (good pattern) — but EOD writes wrong numbers into them | schema misalignment | F13 |
| Orchestration / routing | Conditional edges; run a node only when its inputs changed | Graph is 100% hard edges; every node — deterministic and LLM — fires every tick unconditionally | — | F6, F14, F17 |
| Structured handoffs | Typed, validated contracts between agents | `OptimizationStrategy.shave_kw` is produced, passed, then silently ignored; planner/auditor hand-parse JSON | schema misalignment | F3, F16 |
| Deterministic tool layer | LLM reasons; code computes | MILP is a tool (good) — but the controller LLM only copies its output, and the EOD LLM recomputes metrics by hand and gets them wrong | — | F5, F13 |
| Workflow vs agent honesty | Use a workflow for fixed logic, an agent for dynamic decisions | Controller + planner are deterministic *workflows* wrapped in *agent* call frames | — | F5, F6 |
| Observability | Traces reflect what actually happened | `agent_trace` shows "Target shave 236 kW" while 43 kW is dispatched | state/schema | F3, F11 |

**Summary judgement.** FusionQuad is built *on* a harness (`deepagents`) but does not *use* the harness. It hand-rolls context (re-stuffing a god-object `AgentState` into every prompt), hand-rolls JSON parsing, runs a fixed graph with no routing, and leaves the harness's compression and isolation features switched off. The result is exactly the 2026 failure taxonomy: context drift (F7), schema misalignment (F3, F10, F16), and a forecast/optimizer pipeline that is never reconciled against reality (F1, F2). The multi-agent design is sound in principle — the defects are in the harness layer, which is the documented majority case.

---

## 3. Architecture-level findings

These are not single-line bugs; they shape every flaw below.

**A. The graph is a workflow disguised as a multi-agent system.** Three of the six nodes are LLM agents, but two of those three (planner, controller) make decisions that are fully determined by their inputs — a workflow with predetermined paths, per the LangGraph definition. The agent framing adds latency, token cost, and nondeterministic failure modes (JSON parse failures, structured-output misses) without adding any dynamic decision-making. The fix the project wants is **not** to delete the agents — it is to give them decisions that genuinely require a reasoner (see F5, F6 and §8).

**B. No routing.** `workflow.py` wires only `add_edge` (hard edges). There is not one `add_conditional_edges` or `Command` in the graph. So the graph *cannot* skip a node, *cannot* run the planner only on a regime change, and *cannot* short-circuit on infeasibility. Every flaw that says "should only run when X" is blocked by this single missing capability (F17).

**C. The harness's own context features are switched off.** `deepagents` ships compression, summarization, subagent isolation, and a virtual filesystem. FusionQuad uses the filesystem (`/experience/`, `/strategies/`) but ignores compression/summarization and never delegates to a subagent. Instead it manually rebuilds context every tick by serializing `AgentState` into prompt strings. This is "fighting the harness" — the documented anti-pattern that produces context drift.

**D. `AgentState` is a god-object.** A single `TypedDict` (`state.py`) carries ~35 fields spanning raw data, forecasts, battery physics, tariff, strategy, dispatch, audit accumulators, and workflow metadata. Every agent reads and writes it; nothing is scoped. LangGraph's runtime-context / dependency-injection mechanism (`context_schema`) exists precisely to keep static inputs out of mutable graph state — unused here. This makes the system hard to test in isolation and easy to corrupt (a node can overwrite any field).

---

## 4. Flaws — Critical

### F1 — Forecast is decoupled from actual load; confidence is a fake constant `[forecast]`

- **Symptom:** `forecast_kw` tracks reality poorly. Log tick 0: forecast 1040 kW vs actual 877 kW. Tick 8: forecast 890 kW vs actual baseline ~1231 kW. The model emits a near-flat ~900–1040 band while real load swings 684–1231 kW. `forecast_confidence` is `0.80` on **every** tick.
- **Root cause:** `forecast.py:155 _estimate_confidence` buckets a **single-step, teacher-forced** MAPE (`evaluate_mape` on the validation tail of `prepare_sequence`). The system actually consumes `model.predict_horizon(...)` — a **multi-step autoregressive** rollout whose error compounds. Single-step MAPE is optimistic, so confidence is permanently stuck in the 0.80 (5–15% MAPE) bucket while the autoregressive horizon is far worse. No per-tick forecast-vs-actual error is ever logged, so the defect is invisible to the rest of the system.
- **Fix:** log `forecast[0]` against the realised load every tick; compute a live trailing-window MAPE on the *autoregressive* output and feed that into confidence. Benchmark horizon error with `compare_models.py`; retrain (`train_gru.py`) if horizon MAPE > ~15%. Downstream agents must treat low-confidence forecasts as low-confidence (see F16 gate, §8).
- **Effort:** M
- **Verify:** logged trailing-window MAPE on `predict_horizon` output ≤ 15%; `forecast_confidence` varies tick to tick and correlates with realised error.

### F2 — Forecast is off by one tick; every tick optimizes the *next* interval `[forecast → controller]`

- **Symptom:** the dispatch computed for tick *N* is actually the optimum for tick *N+1*. Peak-shaving acts 30 minutes late.
- **Root cause:** `forecast.py:143 _historical_window` slices `df.iloc[:end_index+1]` with `end_index = current_record_index`, so `predict_horizon` returns predictions for `current_record_index+1 …`. Therefore `forecast_values[0]` is the **next** tick. The controller treats it as the current tick — `controller/node.py:209 forecast_kw = forecast_values[0]` — and `milp_forecast` (passed to MILP as interval 0) starts one tick in the future, while `dispatch_plan[0]` is applied to *this* tick. The controller already holds the true current load in `baseline_load` and never uses it as the forecast head.
- **Fix:** pick one convention. Either make the forecast a nowcast (history ends at `current_record_index-1`, predict `current_record_index …`), or in the controller prepend `baseline_load` as `milp_forecast[0]` and drop the trailing element. Align `forecast_kw` to the same convention.
- **Effort:** S
- **Verify:** for any tick, the forecast's interval-0 timestamp equals `current_time`; MILP interval-0 load equals `baseline_load`.

### F3 — Planner → MILP contract is silently dropped; `shave_kw` is decorative `[planner / controller / solver]`

- **Symptom:** the planner outputs `shave_kw` 125–285 kW with elaborate rationale; the battery discharges ~43–45 kW on every PEAK tick. The dashboard trace shows "Target shave 236 kW" while 43 kW is dispatched — the system misreports its own behaviour. This is textbook **schema misalignment**.
- **Root cause:** two independent breaks. (1) The controller's runtime prompt (`controller/node.py:407`) instructs the LLM to call `milp_optimizer` with `load_forecast=[…]` **only**; `strategy_name`, `shave_kw`, `target_soc_end`, `reserve_soc_pct` are never passed, although the tool signature (`controller/node.py:39`) accepts them. (2) Even when passed, `solver.py:_solve_milp` never references `shave_kw` — it is read only in the error paths `_fallback_discharge` / `_conservative_fallback`. The MILP objective (`solver.py:127`) minimizes `100·peak_demand + energy_cost` with no planner-driven term or floor.
- **Fix:** the controller must pass the full strategy into `milp_optimizer`. In `_solve_milp`, for PEAK intervals add a binding floor — `power[i] >= min(needed_shave, max_d)` where `needed_shave = load[i] - md_limit_kw` — so the planner's intent is *enforced*, not advisory. If the planner is to stay advisory by design, then it must stop emitting a number nobody consumes (see F6). Either the contract binds or the field is removed.
- **Effort:** S
- **Verify:** with planner `shave_kw = X` and feasible SOC, the dispatched discharge ≥ `min(X, max_d, SOC-budget)`; the trace's "target shave" matches the dispatched kW within budget.

### F4 — MILP horizon is a clock-phantom, not the simulation window `[controller / solver]`

- **Symptom:** MILP budgets SOC across far more ticks than the simulation actually runs, so it under-discharges. At 14:00 it assumes 16 PEAK ticks remain; the run ends at 17:00 (6 PEAK ticks). The per-tick sustainable budget collapses from ~83 kW to ~31 kW.
- **Root cause:** `controller/node.py:150 _compute_remaining_peak_ticks` derives the count from the wall clock (`PEAK_END_HOUR=22` minus current time), ignoring that the sim window may end well before 22:00. `_extend_forecast_to_peak` then pads the forecast with the last value across those phantom ticks, stretching one (possibly wrong, per F2) value over an imaginary horizon.
- **Fix:** pass the real remaining ticks into the controller: `remaining_sim_ticks = total_intervals - current_interval`. **Note:** the previous draft of this file proposed `total_intervals - current_record_index`, which is wrong — `current_record_index` is an absolute index into the multi-day CSV (`record_offset + current_interval`), so that expression can go negative. Use `current_interval`. Cap the PEAK horizon at `min(remaining_sim_ticks, clock-based PEAK ticks)`.
- **Effort:** S
- **Verify:** MILP `n_intervals` for any tick equals `min(records_left, peak_ticks_left)` and never exceeds the sim window.

---

## 5. Flaws — High

### F5 — Controller is an LLM that does no LLM-worthy work `[controller]`

- **Symptom:** the controller agent's entire job, per `controller/prompts/system.md` "Normal Operation" and the runtime prompt, is: call `milp_optimizer`, copy `dispatch_action`, return it. An LLM call wrapping one deterministic tool — adding latency, token cost, and JSON/structured-output failure paths (`structured_response` handling, fallback to `_local_milp_fallback`).
- **Root cause:** the agent has no decision to make; MILP already produces the answer. This is a *workflow* in an *agent* frame (§3.A).
- **Fix (keep the agent — give it a real job):** the controller should reason about what MILP cannot: **forecast-vs-reality divergence**. MILP optimizes the forecast; `baseline_load` is the truth. When they disagree (F1/F2), the controller should decide whether to trust the MILP plan, lean toward the `baseline_load`-driven safety floor, or flag infeasibility (F8) — and explain the tradeoff in its structured output. MILP stays a deterministic tool; the agent's value becomes *judgment under forecast uncertainty*, which is genuinely a reasoning task.
- **Effort:** M
- **Verify:** controller output diverges from raw MILP output on ticks where forecast and `baseline_load` differ by >10%, with a logged reason; on agreement ticks it matches MILP.

### F6 — Planner is an LLM that does a deterministic lookup, every tick `[planner]`

- **Symptom:** across the entire weekday log the planner picks `A4 / No Action` for every OFF_PEAK tick and `A7 / A8 / High–Forced Discharge` for every PEAK tick — a pure function of tariff window and SOC band. It is invoked all 48 ticks, each call paying for an LLM round-trip, brace-scraping JSON parsing, and a fallback path.
- **Root cause:** the planner prompt's "Strategy Selection Process" is an `if/else` decision tree; the LLM contributes no judgment over it. Per LangGraph docs this is a **router** ("a single classification step… does not maintain conversation history"), not a supervisor or a reasoning agent.
- **Fix (keep the agent — move its work to where judgment matters):** the per-tick window/SOC classification is a router — make it a lightweight deterministic step. Reserve the *LLM* planner for what actually needs reasoning: pattern-matching `/experience/` history against the current day, detecting anomalies (forecast-confidence collapse, SOC trajectory drifting off-plan), and adapting strategy parameters. Run that reasoning **at session start and on regime changes** (OFF_PEAK→PEAK transition, SOC crossing reserve, day-type change) — enabled by F17's conditional routing — not every tick.
- **Effort:** M
- **Verify:** the planner LLM is invoked ≤ ~3× per session, not per tick; its output cites the `/experience/` file it used; per-tick strategy still updates via the deterministic router.

### F7 — Per-session checkpointer thread → unbounded context growth + stale-state bleed `[planner / controller / auditor]`

- **Symptom:** token cost and latency rise monotonically through a run; late ticks reason over early-tick numbers (**state degradation**).
- **Root cause:** every agent uses a per-*session* thread id — `planner/node.py:156 thread_id=f"planner-{session_id}"`, identical pattern in `controller/node.py:243` and `auditor/agent.py:256`. A LangGraph thread "contains the accumulated state of a sequence of runs"; the `deepagents` checkpointer therefore persists the conversation across all 48 ticks, so tick 48's planner re-reads 48 turns of stale tick state. No `SummarizationMiddleware` is attached to bound it.
- **Fix:** use a per-*tick* thread id (`f"planner-{session_id}-{current_interval}"`) or run the agents stateless (LangGraph runs are stateless by default — omit `thread_id`). Cross-tick memory already flows explicitly via `planner_feedback` and `/experience/` files, so the checkpointer history is redundant *and* harmful. If any agent genuinely needs in-session memory, attach `SummarizationMiddleware` rather than letting the thread grow unbounded.
- **Effort:** S
- **Verify:** agent prompt token count is flat across ticks (not rising); a late-tick agent transcript contains only that tick's state.

### F8 — System blames agents for physically impossible shaves; no infeasibility verdict `[auditor / sim-service]`

- **Symptom:** 27% compliance is reported as agent underperformance. But PEAK baselines reach ~1100–1231 kW against an 800 kW limit (a 300–430 kW breach). A 500 kWh BESS starting at 50% SOC has ~150 kWh usable above the 20% reserve; one 30-minute tick at 350 kW already needs 175 kWh. The battery physically *cannot* meet the limit — yet the auditor still scores it as a failure and the planner keeps escalating.
- **Root cause:** nothing in the loop computes feasibility. `evaluate_rules` / `evaluate_delta` (`auditor/evaluation.py`) score outcomes; no agent emits "the requested shave exceeds installed energy/power for this profile."
- **Fix:** add a deterministic feasibility check (controller or auditor): given SOC, capacity, reserve, max discharge, and remaining breach energy, flag a tick/run `infeasible` when the target is unreachable. Surface it in the log summary and dashboard so non-compliance from undersizing is reported separately from non-compliance from bad decisions. Tie to F9.
- **Effort:** M
- **Verify:** log summary distinguishes `ticks_missed_infeasible` from `ticks_missed_controllable`; a too-small battery yields `infeasible`, not a low agent score.

### F9 — `sizing_advisor.py` is orphaned — the "battery & solar sizing" deliverable is unmet `[sim-service]`

- **Symptom:** `problem_statement.md` requires the solution to "propose automated load shifting strategy **(including solar & battery sizing)**". `SizingAdvisor` is fully implemented (`services/sizing_advisor.py`) but `grep` confirms it is imported nowhere — no route, no workflow node, no UI.
- **Root cause:** never wired in.
- **Fix:** expose it through an API endpoint and the dashboard — after (or before) a run, call `SizingAdvisor.compute(...)` and display recommended BESS kWh / solar kWp / estimated monthly MD savings. Tie it to F8: when a run is `infeasible`, surface the recommended size as the corrective action.
- **Effort:** M
- **Verify:** the dashboard shows a sizing recommendation; the recommended BESS kWh covers the longest MD-breach window of the loaded profile.

### F10 — Planner's strategy decision tree points at files that do not exist `[planner]`

- **Symptom:** `planner/prompts/system.md` step 4 tells the agent to use the `strategy-selector` skill to pick a `/strategies/` file; `CLAUDE.md` names `aggressive_peak_shaving`, `offpeak_valley_fill`, `solar_duck_curve`, `holiday_surge`, `general_bess_guidelines`. The `backend/strategies/` directory contains exactly one file: `Strategy of Battery Action.md`. Every `read_file` for a named strategy fails silently and the agent proceeds on prior knowledge — schema misalignment between prompt, skill, and filesystem.
- **Root cause:** strategy content was consolidated into one file; the prompt, the `strategy-selector` skill, and `CLAUDE.md` were not updated.
- **Fix:** either restore the per-strategy files or rewrite the planner prompt + `strategy-selector` skill + `CLAUDE.md` to reference the single `Strategy of Battery Action.md`. Make the contract match the filesystem.
- **Effort:** S
- **Verify:** every `/strategies/` path named by the planner prompt or the skill resolves to a real file.

### F16 — Planner and auditor don't use `response_format`; brittle hand-rolled JSON parsing `[planner / auditor]`

- **Symptom:** the planner emits free text; `planner/node.py:81 _parse_strategy_payload` tries `json.loads`, then falls back to scraping the first `{` … last `}` substring, then to `_fallback_strategy`. The auditor does the same with `_parse_llm_payload`. When parsing fails the system silently substitutes a generic fallback strategy — a wrong dispatch with no error surfaced.
- **Root cause:** `deepagents` `create_deep_agent` accepts a `response_format` argument; the controller already uses it (`response_format=DispatchAction`) and reads `structured_response`. The planner and auditor agents do not — they parse text by hand.
- **Fix:** pass `response_format=OptimizationStrategy` to the planner agent and a typed schema to the auditor agent; read `structured_response`. Delete the brace-scraping parsers. This converts a silent-wrong-answer path into a validated contract — the documented cure for schema misalignment.
- **Effort:** S
- **Verify:** `_parse_strategy_payload` / `_parse_llm_payload` are gone; planner/auditor outputs are schema-validated; a malformed model output raises rather than silently degrading.

### F17 — The graph has no conditional routing; every node fires every tick `[workflow]`

- **Symptom:** `workflow.py` connects nodes with hard `add_edge` calls only. `data_loader` re-loads the CSV every tick (F14); the planner LLM runs every tick (F6); nothing can be skipped or short-circuited.
- **Root cause:** no `add_conditional_edges` and no `Command`-based routing anywhere in the graph. The graph is structurally a fixed pipeline.
- **Fix:** introduce conditional routing. A routing function (or `Command` returns) should: skip `data_loader` when `loaded_data` is already present (F14); route to the LLM planner only on session start / regime change and to a deterministic strategy step otherwise (F6); allow an early exit / infeasibility branch (F8). This single capability unblocks F6, F8, and F14.
- **Effort:** M
- **Verify:** a steady-state mid-PEAK tick executes only the nodes whose inputs changed; node-execution counts per session are far below `48 × node_count`.

---

## 6. Flaws — Medium

### F11 — MD savings accounting is wrong; dashboard cost figures are inconsistent `[auditor / frontend]`

- **Symptom:** the reported `total_savings_rm` (RM 56.97) is meaningless. MD is billed on the **single highest 30-minute PEAK reading per month** at RM 97.06/kW — it is not a per-tick quantity and not additive.
- **Root cause:** `solver.py:238 _estimate_savings` values discharge at the energy rate only. `auditor/evaluation.py:79` amortizes MD over 1440 intervals and sums it per tick — MD does not amortize. Frontend `live-simulation.ts:187` computes `original_md_cost_rm = originalMd × md_rate`, billing MD on the *entire* peak kW rather than the kW above the limit, and `md_savings_rm` flips between two different formulas (`snapshot.total_savings_rm` OR `peakReductionKw × md_rate`).
- **Fix:** define one MD model and use it everywhere — month MD = max PEAK 30-min kW; MD cost = `MD × 97.06`; MD savings = `(baseline_peak − optimized_peak) × 97.06`, computed once from the run's peak tick. Report energy-arbitrage savings as a separate, clearly-labelled line.
- **Effort:** S
- **Verify:** `md_savings_rm == (max baseline PEAK kW − max optimized PEAK kW) × 97.06`; backend summary and dashboard agree to the cent.

### F12 — MD safety override is a no-op; reserve SOC equals the hard floor `[controller / config]`

- **Symptom:** the PEAK MD-safety override in `controller/node.py:281` never changes the outcome.
- **Root cause:** `max_sustainable_kw = available_kwh / (remaining_peak_ticks·0.5)` uses the inflated clock horizon (F4), so the computed floor lands *below* the MILP output and the override branch is skipped. Separately, `config.py` sets `MIN_SOC = 0.20` (hard hold floor) while the strategy default `reserve_soc_pct` is also `0.20` — the "reserve" gives zero margin above the SOC at which the controller force-holds.
- **Fix:** recompute the override with the corrected horizon (F4). Set `RESERVE_SOC` strictly above `MIN_SOC` (e.g. reserve 0.25 / hard floor 0.15–0.20) so the reserve is a genuine buffer.
- **Effort:** S
- **Verify:** on a tick where MILP under-discharges below the MD-safety floor, the override fires and raises discharge; `reserve_soc_pct > MIN_SOC` holds everywhere.

### F13 — EOD audit lets the LLM do its own arithmetic; it logged a 233% error for a 2.3% reality `[auditor]`

- **Symptom:** `experience/2025-04-07-weekday.md` states `forecast_error_pct ≈ 233.02%` for "forecast 891.86 kW vs actual 912.64 kW" — the true value is ≈ 2.3%. This wrong number is written into a file the planner reads on the next run, poisoning future strategy selection.
- **Root cause:** `evaluate_delta` (`auditor/evaluation.py:70`) computes forecast error correctly, but the EOD prompt (`auditor/agent.py:_build_eod_prompt`) hands the LLM the raw JSON log and asks it to summarize — so the LLM recomputes metrics by hand and gets them wrong. This directly violates the harness principle "do not rely on the LLM for mathematical calculations."
- **Fix:** run `evaluate_delta` / `evaluate_rules` deterministically over the final tick state, inject the computed numbers into the EOD prompt, and instruct the LLM to *quote* them verbatim — never recompute. The LLM's job is narrative, not arithmetic.
- **Effort:** S
- **Verify:** every numeric metric in an `/experience/` file equals the deterministic `evaluate_*` output for that run.

### F14 — `data_loader` and `forecast` re-parse the CSV every tick `[data_loader / forecast]`

- **Symptom:** ~48 redundant CSV reads + DataFrame builds per session.
- **Root cause:** the graph runs `START → data_loader` every tick (F17); `data_loader_node` calls `load_facility_data` → `CSVLoader().load(...)` each time, overwriting identical `loaded_data` already present in `session.state`. `forecast_node` then rebuilds and re-sorts the DataFrame from `payload["data"]` every tick.
- **Fix:** load the CSV once at session start (already done in `SimulationService.start()`). Make `data_loader_node` a conditional no-op when `loaded_data` is present (needs F17), or drop it from the per-tick graph entirely. Cache the parsed/sorted DataFrame per facility.
- **Effort:** S
- **Verify:** the CSV is opened once per session; per-tick wall time drops measurably.

### F15 — Controller prompts contradict each other and the solver `[controller]`

- **Symptom:** `controller/prompts/system.md:47` says call `milp_optimizer` *with* `strategy_name, shave_kw, target_soc_end, reserve_soc_pct`; the runtime prompt (`controller/node.py:407`) says call it with `load_forecast` only; the solver ignores `shave_kw` regardless (F3). Three layers disagree. The system prompt also authorizes the LLM to override MILP output ("change to HOLD") with no deterministic guard — nondeterministic safety behaviour.
- **Root cause:** prompt drift — the static system prompt was not updated when the runtime prompt and solver changed.
- **Fix:** make one prompt the single source of truth, consistent with the F3 fix (strategy passed and binding). Move hard safety overrides (SOC floor, temperature hold) into deterministic code so they are not left to LLM discretion.
- **Effort:** S
- **Verify:** the system prompt, the runtime prompt, and the `milp_optimizer` call site list identical arguments; SOC/temperature holds are enforced in code, not prose.

---

## 7. Minor issues (fix opportunistically)

- `models/forecast_weights.pt` is orphaned — `_MODEL_CONFIGS` references only `gru_weights.pt` / `gru_attention_weights.pt`. Dead file or misnamed.
- `SimulationService.step()` and `run_stream()` duplicate ~60 lines of tick-execution logic — drift risk; extract a shared helper.
- `data_loader_node` docstring claims it returns `md_limit_kw`; it does not.
- `mock_inverter_dispatch` charge path returns `actual_discharge_kw = 0`, so `actual_load` does not rise when charging — a charge tick's grid load is understated in the log.
- Frontend `deriveForecastConfidence` regex-scrapes `(\d+)%` out of a human-readable string instead of reading a structured field — silently breaks if the wording changes.
- `AgentState` god-object (§3.D) — large blast radius; long-term, split static inputs into LangGraph runtime context (`context_schema`).

---

## 8. Target architecture (the corrected harness)

The goal is **not** to remove the LLM agents — it is to make each one a single-responsibility agent with a decision a reasoner is genuinely needed for, and to let the `deepagents` harness do the context work it was built for.

```
START
  └─ data_loader        [conditional: skip if loaded_data present]           ← F14, F17
  └─ forecast ∥ tariff  [forecast = nowcast, interval-0 == current tick]      ← F1, F2
  └─ ROUTER (deterministic)                                                   ← F6, F17
        ├─ regime change / session start ─► planner-LLM (reasoning)
        │       • reads /experience/, detects anomalies, adapts params
        │       • response_format=OptimizationStrategy                        ← F16
        │       • may delegate research to a subagent (holiday check, etc.)
        └─ steady state ─────────────────► strategy-router (rule lookup)
  └─ controller-LLM (judgment under forecast uncertainty)                     ← F5
        • milp_optimizer tool: receives full strategy; shave_kw is a binding  ← F3
          MILP floor; horizon = remaining sim ticks                          ← F4
        • agent reconciles MILP plan vs baseline_load truth, flags infeasible ← F8
        • response_format=DispatchAction (already correct)
  └─ feasibility gate ──► if infeasible, attach SizingAdvisor recommendation  ← F8, F9
  └─ auditor (deterministic scoring + narrative LLM)
        • LLM quotes deterministic evaluate_* numbers, never recomputes       ← F13
        • one MD-cost model shared with frontend                             ← F11
END
```

Harness configuration changes:
- **Threads:** per-tick `thread_id` (or stateless); no unbounded per-session thread (F7).
- **Context:** rely on the harness's compression / `SummarizationMiddleware` if any agent needs in-session memory; stop hand-stuffing `AgentState` into prompts.
- **Routing:** `add_conditional_edges` / `Command` so deterministic and LLM nodes run only when their inputs changed (F17).
- **Contracts:** every agent boundary is a validated `response_format` schema; no hand-parsed JSON (F16).
- **Deterministic layer:** MILP, savings math, feasibility, forecast error — all in code; the LLM reasons and narrates, it never computes a number that code can compute exactly.

This keeps the multi-agent story intact (planner, controller, auditor remain LLM agents) while moving each to a defensible role and closing the three harness-defect classes.

---

## 9. Recommended fix sequence

1. **F2** (forecast off-by-one) — small; unblocks every downstream number.
2. **F1** (forecast accuracy + real confidence) — until the forecast is trusted, the optimizer solves fiction.
3. **F4 + F3** (real horizon + binding `shave_kw`) — planner intent becomes real; MILP budgets the actual window.
4. **F17** (conditional routing) — structural enabler for F6, F8, F14.
5. **F12** (override + reserve margin) — the safety net starts working once F4 lands.
6. **F8 + F9** (infeasibility verdict + wire `SizingAdvisor`) — stop blaming agents for undersizing; satisfy the sizing deliverable.
7. **F7 + F16** (per-tick threads + `response_format`) — close context drift and schema misalignment before adding agent reasoning.
8. **F5 + F6** (give the controller and planner real LLM jobs) — the multi-agent architecture stays; the agents start earning their cost.
9. **F11 + F13 + F10 + F15** (accounting, EOD arithmetic, strategy files, prompt consistency) — correctness and contract cleanup.
10. **F14** + minors — performance and hygiene.

**Bottom line.** F1–F4 are one causal chain: the optimizer is tuned against a forecast that is both inaccurate and time-shifted, then handed a planner number it ignores and a horizon that does not exist. Fix the inputs before tuning the solver. F5–F9 and F16–F17 are the harness layer — and the harness layer is where ~65% of agent systems fail. FusionQuad's multi-agent design is sound; its defects are context drift, schema misalignment, and state degradation. Keep the agents, give them decisions worth a reasoner, let the harness manage context, and make every agent boundary a validated contract.

---

## 10. References

- [Deep Agents overview — "we think of deepagents as an agent harness"](https://docs.langchain.com/oss/python/deepagents/overview)
- [Deep Agents — Context management (input context / compression / isolation / long-term memory)](https://docs.langchain.com/oss/python/deepagents/harness)
- [LangGraph — Persistence & Threads (a thread accumulates state across runs)](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph — Workflows and agents (fixed paths vs dynamic)](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph — Conditional edges & `Command` routing](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangChain — Multi-agent: router vs supervisor vs subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/router)
- [LangChain — Structured output / `response_format`](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain — Summarization middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in)
- [Anthropic — Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Augment Code — Harness engineering for AI agents](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents)
- [Agent Harness Engineering — the AI control plane (failure taxonomy: context drift / schema misalignment / state degradation)](https://medium.com/@adnanmasood/agent-harness-engineering-the-rise-of-the-ai-control-plane-938ead884b1d)
- [A Practical Guide for Production-Grade Agentic AI Workflows (arXiv)](https://arxiv.org/pdf/2512.08769)
