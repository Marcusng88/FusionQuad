# FusionQuad — Engineering Audit

**Date:** 2026-05-17  
**Reviewers (perspective):** Electrical/Electronic Engineer · Agentic AI Engineer · ML Engineer  
**Branch:** `feature/multi-agent-architecture`

---

## Severity Legend

| Tag | Meaning |
|-----|---------|
| `[CRIT]` | Wrong physics / broken logic / safety risk |
| `[HIGH]` | Significant correctness bug or architectural flaw |
| `[MED]` | Suboptimal but not immediately wrong |
| `[LOW]` | Code smell / maintainability |

---

## 1. Electrical & Electronic Engineering — BESS Physics

### 1.1 [CRIT] SOC never clamped on discharge — can go negative

**File:** `backend/app/agents/controller/node.py:114`

```python
new_soc = current_soc - (actual_discharge / bess_capacity_kwh)
```

No `max(new_soc, 0.0)` clamp. If MILP returns a large discharge_kw relative to available energy, SOC becomes negative. Real BMS would disconnect. The solver's MIN_SOC guard only applies during planning, not during the mock inverter execution.

**Fix:** `new_soc = max(0.0, current_soc - (actual_discharge / bess_capacity_kwh))`

---

### 1.2 [CRIT] Temperature never decreases — unbounded thermal accumulation

**File:** `backend/app/agents/controller/node.py:247`

```python
new_temp = temperature_c + raw_result.get("temp_increase_c", 0.0)
```

Every tick adds heat. No cooling model exists. After 48 × 30-min intervals at 100 kW discharge: `30 + 0.5 × 48 = 54 °C`. The rule violation check in `evaluation.py:122` checks *per-tick increase > 5 °C*, not absolute temperature. Real lithium cells derate at 45 °C and enter thermal runaway territory above 60 °C.

**Fix:** Add a thermal decay term each tick (Newton's law of cooling). Add absolute temperature limit check (e.g., 45 °C warning, 55 °C shutdown).

---

### 1.3 [CRIT] Charging ignores round-trip efficiency losses

**File:** `backend/app/agents/controller/node.py:119–120`

```python
# discharge
actual_discharge = energy_kwh * (1 - efficiency_loss_pct)   # 5% loss

# charge
new_soc = min(current_soc + (energy_kwh / bess_capacity_kwh), 0.95)   # no loss!
```

Discharge applies 5% efficiency loss; charging does not. Real lithium-ion BESS has ~92–96% round-trip efficiency — losses occur on both paths. Charging without loss over-estimates SOC and under-estimates grid import during charging intervals.

**Fix:** Apply charge efficiency: `energy_stored = energy_kwh * charge_efficiency` (typically 0.94–0.97).

---

### 1.4 [CRIT] Cycle count decrements during charging — physically wrong

**File:** `backend/app/agents/controller/node.py:122`

```python
cycle_increment = -0.005   # during charge
```

Battery cycles do not decrease when charging. A full charge-discharge cycle = 1 cycle counted at end of discharge. Decrementing during charge makes cycle_count meaningless and will never trigger the 3000-cycle safety rule.

**Fix:** Use `cycle_increment = 0.0` during charge. Accumulate fractional cycles only on discharge: `energy_kwh / (2 × bess_capacity_kwh)` (half-cycle per one-way throughput).

---

### 1.5 [HIGH] MILP has no binary mode variable — simultaneous charge+discharge not prevented

**File:** `backend/app/agents/optimization/solver.py:116–117`

```python
power = [pulp.LpVariable(f"power_{i}", -MAX_CHARGE_KW, MAX_DISCHARGE_KW) for i in range(n_intervals)]
```

Single continuous variable per interval with negative = charge, positive = discharge. Without a binary indicator variable and big-M constraints, mixed-integer semantics are not enforced — the LP relaxation can pick values near zero that represent neither clean charge nor clean discharge. Proper BESS MILP requires:

```python
b[i] = binary  # 1 = discharge mode
p_d[i] >= 0, p_c[i] >= 0
p_d[i] <= MAX_DISCHARGE * b[i]
p_c[i] <= MAX_CHARGE * (1 - b[i])
```

---

### 1.6 [HIGH] MILP SOC dynamics ignore efficiency

**File:** `backend/app/agents/optimization/solver.py:128–129`

```python
prob += soc[i] == soc[i-1] - (energy_kwh / input_data.bess_capacity_kwh)
```

Lossless SOC transition. The planned SOC trajectory will differ from real SOC after execution (which does apply efficiency). Over 48 intervals this divergence is significant and causes mis-dispatch.

---

### 1.7 [HIGH] Inverter efficiency is fixed at 5% — ignores load-dependent derating

**File:** `backend/app/agents/controller/node.py:109`

```python
efficiency_loss_pct = 0.05
```

Real inverter efficiency varies with load. At 10% rated power, efficiency may be 80–85%. At 100% rated power, ~94–97%. Flat 5% loss over-estimates efficiency at low dispatch and under-estimates it at high dispatch.

---

### 1.8 [HIGH] MD savings calculation is wrong — interval energy cost ≠ demand charge

**File:** `backend/app/agents/auditor/evaluation.py:75`

```python
interval_savings_rm = shave_kw * (duration_min / 60) * rate
```

This computes *energy* savings (kWh × RM/kWh). Demand charge (MD) is billed on the **single highest 30-min kW reading per billing month** at RM 97.06/kW. Reducing one interval's peak does not guarantee MD savings unless it's the monthly peak. Multiplying by energy rate and summing interval-by-interval is the wrong model.

**Correct MD savings:** `md_savings = (original_monthly_peak_kw - new_monthly_peak_kw) × 97.06`

---

### 1.9 [MED] No battery capacity degradation over cycles

**File:** `backend/app/agents/state.py`, `solver.py`

`capacity_kwh` is constant throughout the simulation. Real lithium-ion degrades ~20% after 3000–4000 cycles. `cycle_count` is tracked but never fed back to reduce `bess_capacity_kwh`. The MILP will over-dispatch aged batteries.

---

### 1.10 [MED] Tariff window boundary is half-open on wrong side

**File:** `backend/app/agents/tariff/node.py:42`

```python
if 14 <= dt.hour < 22:
    return "PEAK"
```

`dt.hour == 22` maps to OFF_PEAK. TNB C2 tariff peak window is 1400–2200 h. If the timestamp is e.g. 22:00:00, it is actually the start of off-peak, so the code is correct — but any timestamp at exactly 22:00 is off-peak, consistent with TNB definition. However the CSV loader comment says "OFF_PEAK = 10PM - 2PM" which implies the transition is at 22:00. Verify with actual TNB tariff document whether the boundary is inclusive or exclusive.

---

### 1.11 [MED] No power factor / reactive power model

Commercial facilities in Malaysia are billed for reactive power (kVAR) via low power factor penalties. BESS can also provide VAR compensation. Completely absent from this model.

---

### 1.12 [LOW] DT_SECONDS hardcoded at 1800 seconds

**File:** `backend/app/agents/optimization/solver.py:53`

```python
DT_SECONDS = 1800
```

If a CSV with 15-min resolution is loaded, the MILP and savings calculations are wrong by 2×. The interval duration should be derived from the loaded data, not hardcoded.

---

## 2. Agentic AI Engineering — Multi-Agent Architecture

### 2.1 [CRIT] Shared thread_id across concurrent sessions — state contamination

**File:** `backend/app/agents/planner/node.py:125`  
**File:** `backend/app/agents/controller/node.py:210`

```python
config={"configurable": {"thread_id": "planner"}}
config={"configurable": {"thread_id": "controller"}}
```

All simulation sessions use identical thread IDs. LangGraph's memory backend stores conversation state per thread. Two simultaneous users contaminate each other's agent memory. Session A's planner strategy leaks into Session B's context.

**Fix:** Use `thread_id=f"{agent_name}-{session_id}"`.

---

### 2.2 [CRIT] Auditor safety rules skipped when LLM succeeds

**File:** `backend/app/agents/auditor/agent.py:258–295`

```python
rule_eval: RuleEvaluation = {"passed": True, "violations": []}   # default
delta_eval: DeltaEvaluation = {"shave_kw": 0.0, ...}              # default

try:
    result = agent.invoke(...)
    # if LLM succeeds, rule_eval and delta_eval remain as empty defaults
    ...
except:
    # ONLY HERE does real evaluate_rules / evaluate_delta get called
```

The primary execution path (LLM agent succeeds) never calls `evaluate_rules`. Safety checks only run on fallback. This means SOC violations, over-temperature, and inverter limit breaches are silently ignored when the LLM responds successfully.

**Fix:** Always call `evaluate_rules` and `evaluate_delta` first, then pass results to LLM for reasoning.

---

### 2.3 [HIGH] Global singleton agents re-create backend every call

**File:** `backend/app/agents/auditor/agent.py:131–133`

```python
def _get_auditor_agent(system_prompt: str, is_eod: bool) -> object:
    global _AUDITOR_AGENT_TICK, _AUDITOR_AGENT_EOD
    backend = _build_auditor_backend()   # new backend instance every call
    if is_eod:
        if _AUDITOR_AGENT_EOD is None:
            ...create agent with this backend...
        return _AUDITOR_AGENT_EOD        # cached agent has OLD backend
```

A new `CompositeBackend` is instantiated every tick but the cached agent ignores it (used only at construction time). Both wasteful and misleading.

---

### 2.4 [HIGH] Controller always uses `current_dispatch_index=0` — throws away multi-step plan

**File:** `backend/app/agents/controller/node.py:79`, `backend/app/agents/optimization/solver.py:169`

```python
current_dispatch_index=0,   # always tick 0
```

The MILP solver computes an N-interval optimal dispatch plan but the controller always executes only the first interval and discards the rest. The intended receding horizon control (MPC) requires re-using the plan and advancing the index. Instead, the system solves a new MILP from scratch every tick — expensive and inconsistent.

---

### 2.5 [HIGH] No agent invocation timeout

`agent.invoke()` in planner, controller, and auditor nodes has no timeout. A slow LLM API response blocks the async loop indefinitely. FastAPI workers pile up, starving other requests.

**Fix:** Wrap with `asyncio.wait_for()` or pass `timeout` config to the agent.

---

### 2.6 [HIGH] `run_stream` yields inside held lock

**File:** `backend/app/services/simulation.py:225–296`

```python
async with session.lock:
    ...
    async for chunk in self._workflow.astream(...):
        yield {...}   # yielding inside lock!
```

Yielding inside `async with session.lock` holds the lock for the entire streaming duration (multiple LLM calls, potentially seconds). Any concurrent `get_state` or `step` call on the same session blocks completely.

**Fix:** Collect all tick results, release lock, then yield.

---

### 2.7 [HIGH] `shave_percentage` formula is wrong

**File:** `backend/app/agents/auditor/agent.py:343–347`

```python
total_possible_shave = baseline_load - md_limit_kw if baseline_load > md_limit_kw else 0
...
shave_percentage = (total_shave / (total_possible_shave * len(new_decision_log))) * 100
```

`total_possible_shave` is derived from the **current tick's** `baseline_load`. This single-tick value is then multiplied by interval count to make a denominator. If the current tick has low baseline (e.g., off-peak), `total_possible_shave = 0` → `shave_percentage = 0`. This metric is misleading and numerically unstable.

---

### 2.8 [HIGH] `session.state = result` may lose keys on partial LangGraph update

**File:** `backend/app/services/simulation.py:180`

```python
session.state = result
```

LangGraph's `invoke` may return only updated keys (delta), not the full state. Overwriting `session.state` with a partial dict drops unchanged keys from previous ticks.

**Fix:** `session.state = {**session.state, **result}` or rely on LangGraph's compiled graph to return full state.

---

### 2.9 [HIGH] Workflow is strictly sequential — no parallelism

**File:** `backend/app/agents/workflow.py`

```
data_loader → forecast → tariff → planner → controller → auditor
```

`forecast` and `tariff` are independent — both depend only on `data_loader` output. Running them sequentially adds one full LLM round-trip of latency per tick. LangGraph supports parallel branches via `add_edge` to multiple nodes.

---

### 2.10 [MED] `mock_inverter_dispatch` decorated with `@tool` but never used by any agent

**File:** `backend/app/agents/controller/node.py:90`

```python
@tool
def mock_inverter_dispatch(...):
```

The controller agent's tools list is `tools=[milp_optimizer]` — `mock_inverter_dispatch` is not included. The `@tool` decorator is pointless; the function is called directly via `.invoke()` in `_execute_dispatch`. The controller prompt also explicitly says "Do NOT call mock_inverter_dispatch". Remove the decorator.

---

### 2.11 [MED] No retry / exponential backoff on LLM failures

All three agents (`planner`, `controller`, `auditor`) silently fall back on any exception. Transient API errors (rate limit, network timeout) trigger permanent fallback for that tick. Production systems need retry with backoff before falling back.

---

### 2.12 [MED] Planner agent has empty tools list but prompt promises filesystem access

**File:** `backend/app/agents/planner/node.py:49`

```python
tools=[],
```

The planner prompt instructs the agent to "Use read_file to read strategy files". The `backend` parameter provides a `FilesystemBackend`, but `read_file` is a built-in DeepAgents tool injected by the framework — it's unclear whether this is actually available without explicit declaration. The empty tools list makes this fragile.

---

### 2.13 [MED] `asyncio.get_event_loop()` deprecated since Python 3.10

**File:** `backend/app/services/simulation.py:73`, `350`

```python
loop = asyncio.get_event_loop()
```

In async context, use `asyncio.get_running_loop()`. `get_event_loop()` emits a DeprecationWarning in Python 3.10+ and may return a closed loop.

---

### 2.14 [MED] Session store grows unbounded — memory leak

**File:** `backend/app/services/simulation.py:59`

```python
self._sessions: dict[str, SimulationSession] = {}
```

Sessions are added on `start()` but never evicted. A long-running server accumulates all historical sessions in memory. No TTL, no max-session limit, no cleanup on completion.

---

### 2.15 [LOW] MD rate duplicated in two places

`MD_RATE = 97.06` in `simulation.py:25` and `demand=97.06` in `tariff/rates.py:14`. Two sources of truth — must be kept in sync manually.

---

## 3. Machine Learning Engineering — GRU Forecasting

### 3.1 [CRIT] Dead code after `return` in `prepare_sequence`

**File:** `backend/app/ml/forecast_model.py:93–111`

```python
return torch.from_numpy(X), torch.from_numpy(y)
seq_len = self.config.seq_len        # UNREACHABLE

if len(values) < seq_len + 1:        # UNREACHABLE
    ...
X_list = []                           # UNREACHABLE — duplicate block
```

Lines 94–111 are completely unreachable dead code — a duplicate of the sliding window loop that was accidentally left after the return statement. This is a copy-paste error.

---

### 3.2 [CRIT] `torch.load(..., weights_only=False)` — arbitrary code execution risk

**File:** `backend/app/ml/forecast_model.py:192`

```python
checkpoint = torch.load(path, weights_only=False)
```

`weights_only=False` uses Python's `pickle` deserializer. Loading a maliciously crafted `.pt` file executes arbitrary code. A compromised model file = remote code execution on the server.

**Fix:** `weights_only=True` (requires torch ≥ 1.13). Serialize config separately as JSON.

---

### 3.3 [CRIT] Model reloaded from disk every tick for every facility

**File:** `backend/app/agents/forecast.py:39–41`

```python
model = ForecastModel()
if model_path.exists():
    model.load(model_path)
```

This runs inside `for facility, payload in loaded.items()` which runs every workflow tick. Each tick reads and deserializes the model weights from disk. For a 48-tick simulation with 1 facility: 48 disk reads and weight copies. 

**Fix:** Cache the loaded model at module level, reload only on startup or file change.

---

### 3.4 [HIGH] Data leakage: `_min_val/_max_val` overwritten between confidence and prediction

**File:** `backend/app/agents/forecast.py:44–47`

```python
confidence = _estimate_confidence(model, history)    # calls prepare_sequence → sets _min_val/_max_val
forecast_values = _predict_horizon(model, history, horizon)  # calls prepare_sequence again → OVERWRITES _min_val/_max_val
```

`_estimate_confidence` calls `model.prepare_sequence(history)` setting normalization stats. Then `_predict_horizon` calls `model.prepare_sequence(history)` again, overwriting those stats. The `mape` calculation inside `_estimate_confidence` uses one set of stats; the denormalization in `_predict_horizon` uses a re-derived set. If history slices differ (they shouldn't here), normalization diverges silently.

More critically: `evaluate_mape` inside `_estimate_confidence` denormalizes predictions using `_min_val/_max_val` from the *full history* sequence, but `y_val` targets are from the 80% split which was normalized with *full history* stats — so the MAPE computation is consistent. But the issue is ordering: `_estimate_confidence` is called first and leaves stats from full `history`; then `_predict_horizon` calls `prepare_sequence(history)` again which resets stats identically. In practice, same stats → no bug, but this is fragile coupling through shared mutable state.

---

### 3.5 [HIGH] Training shuffles time-series data — temporal leakage

**File:** `backend/app/ml/forecast_model.py:124`

```python
dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
```

Shuffling destroys temporal order. For a sliding window dataset, future windows contain values that are part of past windows' targets. When batches are shuffled, the model trains on sequences where it has implicitly seen future information through overlapping windows with different targets. Use chronological batching for time-series.

**Fix:** `shuffle=False` for time-series training. Use walk-forward validation.

---

### 3.6 [HIGH] `_predict_horizon` doesn't call `model.eval()` — dropout active during inference

**File:** `backend/app/agents/forecast.py:107–126`

```python
def _predict_horizon(model: ForecastModel, history: pd.DataFrame, horizon: int) -> list[float]:
    X, _ = model.prepare_sequence(history)
    seq = X[-1:].clone()
    ...
    for _ in range(horizon):
        with torch.no_grad():
            normalized = model.model(seq).reshape(-1)[0]   # model in train mode!
```

`model.model.eval()` is never called in `_predict_horizon`. GRU dropout layers remain active, making predictions stochastic and different across calls with the same input. `ForecastModel.predict()` does call `self.model.eval()` but `_predict_horizon` bypasses it by calling `model.model(seq)` directly.

---

### 3.7 [HIGH] Model used without training if weights file absent — silent random predictions

**File:** `backend/app/agents/forecast.py:39–41`

```python
model = ForecastModel()
if model_path.exists():
    model.load(model_path)
# else: randomly initialized model used silently
```

If `forecast_weights.pt` is missing, a randomly initialized GRU produces garbage predictions with no warning logged. The rest of the pipeline treats this output as valid. Should at minimum raise an exception or log a critical warning.

---

### 3.8 [HIGH] Autoregressive multi-step prediction compounds error unchecked

**File:** `backend/app/agents/forecast.py:112–126`

Each step's predicted value is fed as input to the next step. Forecast error at step _t_ is the input error for step _t+1_. Over 6 steps (3-hour horizon), error can drift substantially. No confidence intervals, no uncertainty quantification, no warning when error exceeds a threshold.

---

### 3.9 [MED] Univariate model ignores all exogenous features

The GRU uses only `kw_import` (univariate). Excluded:
- Time-of-day / hour encoding
- Day-of-week
- Solar irradiance / kWp installed
- Ambient temperature (affects HVAC load)
- Holiday indicator

For solar duck-curve scenario especially, solar generation is a primary predictor of afternoon ramp. The model cannot capture this.

---

### 3.10 [MED] MAPE-based confidence thresholds are arbitrary

**File:** `backend/app/agents/forecast.py:97–104`

```python
if mape <= 5:   return 0.95
if mape <= 15:  return 0.80
if mape <= 30:  return 0.60
return 0.40
```

These thresholds are hardcoded without empirical calibration. A model with MAPE=14.9% returns confidence=0.80 while MAPE=15.1% returns 0.60 — a discontinuous cliff. Calibrate using isotonic regression or Platt scaling.

---

### 3.11 [MED] No model versioning or A/B evaluation

Single `forecast_weights.pt` — no version metadata, no hash check, no A/B test infrastructure. Retraining overwrites production weights with no rollback.

---

### 3.12 [MED] Validation set in `_estimate_confidence` leaks through overlapping windows

**File:** `backend/app/agents/forecast.py:91–97`

```python
split = max(1, int(0.8 * n))
X_val = X[split:]
y_val = y[split:]
```

Sliding window sequences overlap: window at index `i` shares `seq_len-1` timesteps with window at index `i+1`. Splitting at 80% of windows means training windows include timesteps that appear in validation targets. This is temporal leakage — validation MAPE is optimistic.

---

### 3.13 [LOW] `forecast_window` defaults to 6 intervals but GRU predicts one-step-ahead

**File:** `backend/app/agents/forecast.py:23`

The model architecture (`output_size=1`) predicts exactly one step. Multi-step horizon is achieved via autoregressive rollout in `_predict_horizon`. The `forecast_window` parameter of 6 means 6 autoregressive steps — this should be documented as such and its error-compounding property acknowledged.

---

## 4. Summary Table

| # | File | Severity | Domain | Issue |
|---|------|----------|--------|-------|
| 1.1 | `controller/node.py:114` | CRIT | EE | SOC can go negative on discharge |
| 1.2 | `controller/node.py:247` | CRIT | EE | Temperature never cools — unbounded |
| 1.3 | `controller/node.py:119` | CRIT | EE | Charging ignores efficiency loss |
| 1.4 | `controller/node.py:122` | CRIT | EE | Cycle count decrements on charge |
| 1.5 | `solver.py:116` | HIGH | EE | No binary mode var — charge+discharge not exclusive |
| 1.6 | `solver.py:128` | HIGH | EE | MILP SOC dynamics lossless — diverges from real execution |
| 1.7 | `controller/node.py:109` | HIGH | EE | Fixed 5% efficiency ignores load curve |
| 1.8 | `evaluation.py:75` | HIGH | EE | MD savings = energy rate × kWh — wrong for demand charge |
| 1.9 | `state.py` | MED | EE | No capacity degradation with cycles |
| 1.10 | `tariff/node.py:42` | MED | EE | Verify TNB peak boundary inclusivity |
| 1.11 | — | MED | EE | No reactive power / power factor model |
| 1.12 | `solver.py:53` | LOW | EE | DT_SECONDS hardcoded — breaks for non-30min data |
| 2.1 | `planner/node.py:125` | CRIT | AI | Shared thread_id — cross-session contamination |
| 2.2 | `auditor/agent.py:258` | CRIT | AI | Safety rules only run on LLM fallback path |
| 2.3 | `auditor/agent.py:131` | HIGH | AI | Backend rebuilt every call but agent cached with old one |
| 2.4 | `controller/node.py:79` | HIGH | AI | Always dispatch_index=0 — MPC plan discarded |
| 2.5 | all agents | HIGH | AI | No LLM invocation timeout |
| 2.6 | `simulation.py:225` | HIGH | AI | Yield inside lock — deadlock risk |
| 2.7 | `auditor/agent.py:343` | HIGH | AI | shave_percentage formula is numerically wrong |
| 2.8 | `simulation.py:180` | HIGH | AI | State overwrite may drop unchanged keys |
| 2.9 | `workflow.py` | HIGH | AI | Sequential pipeline — forecast+tariff could be parallel |
| 2.10 | `controller/node.py:90` | MED | AI | @tool on mock_inverter_dispatch — never used by agent |
| 2.11 | all agents | MED | AI | No retry / backoff on LLM errors |
| 2.12 | `planner/node.py:49` | MED | AI | Empty tools list vs. prompt promising read_file |
| 2.13 | `simulation.py:73` | MED | AI | get_event_loop() deprecated |
| 2.14 | `simulation.py:59` | MED | AI | Session dict unbounded — memory leak |
| 2.15 | `simulation.py:25` | LOW | AI | MD rate duplicated — two sources of truth |
| 3.1 | `forecast_model.py:93` | CRIT | ML | Dead code after return in prepare_sequence |
| 3.2 | `forecast_model.py:192` | CRIT | ML | weights_only=False — arbitrary code execution |
| 3.3 | `forecast.py:39` | CRIT | ML | Model reloaded from disk every tick |
| 3.4 | `forecast.py:44` | HIGH | ML | _min_val/_max_val overwritten between confidence and predict |
| 3.5 | `forecast_model.py:124` | HIGH | ML | Shuffle=True on time-series — temporal leakage |
| 3.6 | `forecast.py:114` | HIGH | ML | eval() not called — dropout active during inference |
| 3.7 | `forecast.py:39` | HIGH | ML | Silent random predictions if weights file missing |
| 3.8 | `forecast.py:112` | HIGH | ML | Autoregressive error compounds over horizon |
| 3.9 | `forecast_model.py` | MED | ML | Univariate only — no exogenous features |
| 3.10 | `forecast.py:97` | MED | ML | Arbitrary MAPE thresholds — discontinuous confidence |
| 3.11 | — | MED | ML | No model versioning or rollback |
| 3.12 | `forecast.py:91` | MED | ML | Overlapping window split leaks into validation |
| 3.13 | `forecast.py:23` | LOW | ML | Autoregressive horizon not documented |

---

## 5. Priority Fix Order

1. **[CRIT-EE]** SOC negative clamp + cycle count fix — prevents nonsensical battery state
2. **[CRIT-AI]** Fix auditor fallback logic — safety rules must always run
3. **[CRIT-AI]** Fix thread_id to be session-scoped — prevents cross-session state pollution
4. **[CRIT-ML]** Remove dead code in `prepare_sequence` + add `model.eval()` in predict
5. **[CRIT-ML]** Cache model at module level — fix performance + disk I/O per tick
6. **[HIGH-EE]** Fix MD savings formula — demand charge is monthly peak, not interval energy
7. **[HIGH-EE]** Add charging efficiency loss to mock inverter
8. **[HIGH-AI]** Fix yield-inside-lock in `run_stream`
9. **[HIGH-AI]** Add agent invocation timeout
10. **[HIGH-ML]** Fix shuffle=False for time-series training
