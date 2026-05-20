# Agent Spec: Forecasting

## Purpose

Generate rolling 30-minute ahead load forecasts using the pre-trained GRU model. Produces `load_forecast` and `forecast_confidence` that Planner consumes for strategy decisions and Auditor uses for evaluation.

## Type

**Custom node** (not a Deep Agent) — deterministic model inference, no ReAct loop.

## Position in Pipeline

```
[DataLoader] → [Forecasting] → [Tariff] → [Planner] → ...
```

Forecasting runs **every simulation tick** (every 30 simulated minutes).

---

## Input

| Source | Description |
|--------|-------------|
| `state.loaded_data[facility]["data"]` | DataFrame with `datetime` and `kw_import` columns |
| `state.current_time` | Current simulation datetime |
| `state.forecast_window` | Number of intervals to forecast (default 1 = next 30 min) |

---

## Output

Written to `AgentState`:

| Key | Type | Description |
|-----|------|-------------|
| `load_forecast` | `dict[str, list[float]]` | `{facility: [val_t+1, val_t+2, ...]}` — next N interval predictions in kW |
| `forecast_confidence` | `dict[str, float]` | `{facility: 0.0–1.0}` — model confidence score |

---

## State Schema (partial)

```python
class AgentState(TypedDict):
    load_forecast: dict[str, list[float]] | None
    forecast_confidence: dict[str, float] | None
    loaded_data: dict[str, dict] | None
    current_time: datetime | None
    forecast_window: int | None  # default 1
```

---

## Logic

```
1. Receive current_time from state
2. For each facility in loaded_data:
   a. Extract sliding window of last seq_len (48) readings from kw_import
   b. Feed into ForecastModel.predict() → denormalized kW value
   c. Compute confidence via evaluate_mape() on last 20% of training data
   d. Append forecast to load_forecast[facility]
3. Return {load_forecast, forecast_confidence}
```

**Rolling forecast detail:**
- Uses last known actual reading at `current_time` as anchor
- Predicts exactly 1 interval ahead (30 min) per tick
- On next tick, actual reading replaces forecast, model re-runs

**Confidence scoring:**
```python
if mape <= 5:   confidence = 0.95
elif mape <= 15: confidence = 0.80
elif mape <= 30: confidence = 0.60
else:            confidence = 0.40
```

---

## Tools

| Tool | Source | Purpose |
|------|--------|---------|
| `ForecastModel.prepare_sequence(df) → (X, y)` | Existing `app.ml.forecast_model` | Build sliding window tensors |
| `ForecastModel.predict(X) → float` | Existing `app.ml.forecast_model` | GRU inference → kW value |
| `ForecastModel.evaluate_mape(X_val, y_val) → float` | Existing `app.ml.forecast_model` | MAPE → confidence |
| Pre-trained weights | `backend/models/forecast_weights.pt` | Loaded at startup (fallback: random init) |

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Insufficient data for seq_len (48 rows) | Return empty forecast, confidence = 0.0, log warning |
| Model weights file missing | Initialize fresh model, warn — forecast less reliable |
| NaN in kw_import column | Skip interval, use last valid value |
| All intervals identical | Predict same value, confidence = 0.5 |

---

## Acceptance Criteria

- [ ] Forecast runs every simulation tick (not once)
- [ ] Output format: `{facility: [next_interval_kw, ...]}` — list of floats
- [ ] Confidence is 0.0–1.0 per facility
- [ ] Prediction is denormalized to actual kW (not 0-1 normalized)
- [ ] Handles missing model weights gracefully (no crash)
- [ ] `test_forecast.py` passes with MAPE ≤ 15% on validation set

---

## Dependencies

- Reads: `state.loaded_data`, `state.current_time`
- Writes: `state.load_forecast`, `state.forecast_confidence`
- Model: `backend/models/forecast_weights.pt`

---

## File Location

```
backend/app/agents/forecast.py      # node implementation (replace existing)
backend/app/ml/forecast_model.py    # ForecastModel class (existing)
backend/models/forecast_weights.pt  # pre-trained weights
```
