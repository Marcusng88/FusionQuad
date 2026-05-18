# Grid Import Forecast — ML Improvement Proposal

> Date: 2026-05-19  
> Author: AI/ML Research Analysis  
> Context: FusionQuad energy management system, Malaysian commercial facilities

---

## 1. Current State

| Component | Detail |
|-----------|--------|
| Model | GRU + Bahdanau Attention |
| Features | 6: `kw_import`, `hour_sin`, `hour_cos`, `day_sin`, `day_cos`, `is_peak` |
| Sequence length | 48 steps (24hr lookback) |
| Forecast horizon | 6 steps (3hr ahead) |
| Data per facility | ~1,400–2,900 rows (~1 month, 30-min intervals) |
| Output | Point forecast only |
| Normalization | Min-max global |
| Evaluation metric | MAPE |

### Saved Models

| File | Size | Type |
|------|------|------|
| `backend/models/gru_weights.pt` | 155.8 KB | GRU baseline (univariate) |
| `backend/models/gru_attention_weights.pt` | 228.7 KB | GRU + Bahdanau Attention |

---

## 2. Critical Weaknesses

### 2.1 No Weather Data
Tropical commercial buildings — cooling load dominates consumption. No temperature or humidity input means model is blind to the primary driver of load variation.

### 2.2 Missing Lag Features
`t-48` (yesterday same time) and `t-336` (1 week ago) are the two highest-signal features in load forecasting literature. Current model only uses last 48 consecutive steps — misses weekly seasonality entirely.

### 2.3 Point Forecast Only
Optimization agent makes peak shaving decisions with no uncertainty estimate. Malaysian MD charge is RM 97.06/kW — one missed peak costs significant money. Probabilistic bounds required for safe operation.

### 2.4 Small Dataset
~1 month of data per facility is below the threshold where deep models generalize reliably. Overfitting risk is high. Current pooled training loses facility-specific identity.

### 2.5 No Cross-Facility Learning
4 facilities exist in dataset. Each trained independently or pooled uniformly — neither approach captures transfer signal between similar facilities.

---

## 3. Proposed Improvements

### Tier 1 — Quick Wins (Low effort, high return)

#### A. Add Lag Features
Expand input feature set without changing model architecture. Just increase `input_size`.

```python
# New features to add
lag_features = [
    "kw_import_lag_48",    # yesterday same time
    "kw_import_lag_336",   # 1 week ago same time
    "rolling_mean_24h",    # 24hr rolling average
    "rolling_std_24h",     # 24hr rolling std dev
    "rolling_mean_48h",    # 48hr rolling average
]
# input_size: 6 → 11
```

Expected improvement: **10–20% MAPE reduction**. No architecture change needed.

#### B. Quantile Heads on Existing GRU
Add parallel output heads for uncertainty quantification. Optimization agent uses q90 for conservative peak protection.

```python
class GRUQuantileHead(nn.Module):
    def __init__(self, hidden_size, horizon, quantiles=[0.1, 0.5, 0.9]):
        super().__init__()
        self.quantiles = quantiles
        self.heads = nn.ModuleList([
            nn.Linear(hidden_size, horizon) for _ in quantiles
        ])

    def quantile_loss(self, preds, target):
        losses = []
        for i, q in enumerate(self.quantiles):
            err = target - preds[i]
            losses.append(torch.max(q * err, (q - 1) * err).mean())
        return sum(losses)
```

Output: `{q10: [...], q50: [...], q90: [...]}` per horizon step.

#### C. Solar Elevation Angle Feature
Better than binary `is_peak` flag. Free, no API needed — derived from timestamp + coordinates.

```python
from pysolar.solar import get_altitude
from datetime import timezone

# Kuala Lumpur coordinates
LAT, LON = 3.1390, 101.6869

def solar_elevation(dt):
    dt_utc = dt.replace(tzinfo=timezone.utc)
    angle = get_altitude(LAT, LON, dt_utc)
    return max(0.0, angle)  # clamp negative (night) to 0
```

Especially important for `SoL` and `Mi2` solar facilities.

---

### Tier 2 — Model Architecture Upgrade (Medium effort)

#### D. iTransformer (ICLR 2024 Spotlight)
**Best choice when weather features are added.**

- Inverts attention mechanism: embeds variates (features) instead of timestamps
- Captures cross-variate correlations (e.g., temperature ↔ kw_import)
- SOTA on ECL (Electricity Consuming Load) benchmark dataset
- Drop-in replacement for GRU encoder block

```python
# Key config for your problem
config = {
    "seq_len": 48,
    "pred_len": 6,
    "enc_in": 11,        # number of input features
    "d_model": 128,
    "n_heads": 8,
    "e_layers": 3,
    "d_ff": 256,
    "dropout": 0.1,
}
```

Expected improvement: **20–35% MAPE reduction** vs current GRU+Attention when using multivariate features.

#### E. PatchTST
**Best choice if keeping current feature set (no weather).**

- Divides time series into patches → transformer processes patch tokens
- Captures both local (within-patch) and global (across-patch) temporal patterns
- Consistently outperforms iTransformer in univariate settings
- Patch size 16–32 for 30-min intervals = 8–16hr temporal segments

```python
config = {
    "patch_len": 16,     # 8hr patches
    "stride": 8,
    "seq_len": 96,       # extend lookback to 48hr
    "pred_len": 6,
    "d_model": 128,
    "n_heads": 16,
}
```

#### F. N-HiTS (Baseline Alternative)
Pure MLP, no attention. Fast training, small data friendly, less overfitting risk.

- Multi-scale decomposition via hierarchical interpolation
- Better than N-BEATS for multi-step forecasting
- Complexity: Easy — good as quick benchmark upgrade

---

### Tier 3 — Data Strategy (Solves root cause)

#### G. Zero-Shot Foundation Model Baseline
Use pretrained model on your data immediately — no training required. Critical for 1-month dataset regime.

| Model | Params | Zero-shot quality | Notes |
|-------|--------|-------------------|-------|
| MOIRAI-2 (Salesforce) | Large | Excellent | Trained on 27B+ observations across 9 domains |
| Chronos (Amazon) | T5-based | Good | Probabilistic, consumer hardware friendly |
| TimesFM (Google) | 200M | Good | Best for 96–168hr context window |

```bash
pip install uni2ts  # MOIRAI
pip install chronos-forecasting  # Chronos
```

Use these as benchmark ceiling. If your trained model can't beat zero-shot, data pipeline needs work first.

#### H. Cross-Facility Transfer Learning
Train on data-rich facility → fine-tune on sparse facility. Literature shows **56.8% improvement** vs training from scratch on limited data.

```
Strategy:
1. Pre-train on Mi2 (2929 rows, solar) + E (2928 rows)
2. Fine-tune on SoL (1390 rows) — last 3 layers only
3. Freeze encoder, only update prediction head for each facility
```

Facility similarity matrix guides transfer direction:
- Solar → Solar: SoL ← Mi2 (both have solar)
- No-solar → No-solar: E ← SuN

#### I. Synthetic Data Augmentation
Use MOIRAI or Chronos to generate synthetic load profiles. Augment training set for edge cases (extreme demand days, solar ramp events).

---

### Tier 4 — Probabilistic Forecasting

#### J. Conformalized Quantile Regression (CQR)
Wrap any point model with distribution-free coverage guarantee. No model retraining needed.

```python
from mapie.regression import MapieTimeSeriesRegressor
from mapie.subsample import BlockBootstrap

mapie = MapieTimeSeriesRegressor(
    estimator=your_model,
    method="enbpi",
    cv=BlockBootstrap(n_resamplings=10, length=48),
    agg_function="mean",
)
mapie.fit(X_train, y_train)
y_pred, y_pis = mapie.predict(X_test, alpha=0.1)  # 90% coverage
```

For peak shaving: use upper bound `y_pis[:, 1]` (q90) as conservative demand estimate.

---

## 4. Extra Data Requirements

| Data | Why Needed | Source | Cost |
|------|-----------|--------|------|
| Temperature + humidity | Primary cooling load driver | Open-Meteo API | Free |
| GHI (solar irradiance) | Net load for solar facilities | Open-Meteo / NASA POWER | Free |
| Malaysia public holidays | Occupancy pattern proxy | `holidays` Python library | Free |
| DNI, cloud cover | Solar PV output correlation | Open-Meteo | Free |
| Additional months | Model generalization | Facility operator | Operational |

### Open-Meteo Weather Fetch Example

```python
import openmeteo_requests
import pandas as pd

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 3.1390,   # Kuala Lumpur
    "longitude": 101.6869,
    "hourly": ["temperature_2m", "relativehumidity_2m", 
               "direct_radiation", "diffuse_radiation"],
    "start_date": "2025-05-30",
    "end_date": "2025-06-30",
    "timezone": "Asia/Kuala_Lumpur",
}
# Resample to 30-min, align with kw_import timestamps
```

No API key required. Historical data available from 1940.

---

## 5. Feature Engineering Checklist

### Time Features (add to all models)
- [x] `hour_sin`, `hour_cos` — already present
- [x] `day_sin`, `day_cos` — already present
- [x] `is_peak` — already present
- [ ] `month_sin`, `month_cos` — seasonal signal
- [ ] `is_holiday` — Malaysia public holiday flag
- [ ] `is_weekend` — distinct from day_of_week encoding

### Lag Features (add immediately)
- [ ] `kw_import_lag_48` — yesterday same time
- [ ] `kw_import_lag_336` — 1 week ago same time
- [ ] `rolling_mean_24h` — smoothed baseline
- [ ] `rolling_std_24h` — volatility signal
- [ ] `rolling_max_48h` — peak demand context

### Weather Features (after data fetch)
- [ ] `temperature_2m` — cooling load driver
- [ ] `relative_humidity` — wet bulb effect
- [ ] `ghi` — solar output correlation
- [ ] `cloud_cover` — irradiance proxy
- [ ] `solar_elevation_angle` — PV output shape

### Solar-Specific (for SoL, Mi2 facilities)
- [ ] `solar_elevation_angle` — via pysolar
- [ ] `clearness_index = ghi / ghi_clear_sky` — cloud impact
- [ ] `lagged_ghi_1h` — thermal lag effect

---

## 6. Implementation Roadmap

```
Week 1 — Quick Wins
├── Add lag features (t-48, t-336, rolling stats)
├── Retrain GRU+Attention with input_size: 6 → 11
├── Add quantile heads (q10/q50/q90)
└── Benchmark MAPE before/after

Week 2 — Data Pipeline
├── Fetch Open-Meteo weather for facility location
├── Align weather to 30-min intervals
├── Add solar elevation angle via pysolar
└── Rebuild training dataset with full feature set

Week 3 — Model Upgrade
├── Implement iTransformer with weather features
├── Run compare_models.py → GRU vs GRU+Attention vs iTransformer
├── Cross-facility transfer: pre-train on Mi2, fine-tune on SoL
└── Target MAPE < 10% on validation

Week 4 — Probabilistic + Production
├── Add CQR wrapper (MAPIE library)
├── Update forecast_node to output q10/q50/q90
├── Update optimization agent to use q90 for peak protection
└── Run MOIRAI-2 zero-shot as ceiling benchmark
```

---

## 7. Expected Outcomes

| Improvement | Current MAPE Est. | Target MAPE | Method |
|-------------|------------------|-------------|--------|
| Lag features only | ~15–25% | ~12–20% | Feature engineering |
| + Weather data | ~12–20% | ~8–15% | Data enrichment |
| + iTransformer | ~8–15% | ~5–10% | Architecture upgrade |
| + Transfer learning | ~5–10% | ~4–8% | Small data strategy |
| Zero-shot MOIRAI-2 | — | ~8–12% | Benchmark reference |

---

## 8. References

- [iTransformer: Inverted Transformers Are Effective for Time Series Forecasting (ICLR 2024)](https://arxiv.org/abs/2310.06625)
- [PatchTST: A Time Series is Worth 64 Words (ICLR 2023)](https://arxiv.org/abs/2211.14730)
- [TimeMixer: Decomposable Multiscale Mixing (ICLR 2024)](https://openreview.net/pdf?id=7oLshfEIC2)
- [N-HiTS: Neural Hierarchical Interpolation for Time Series (AAAI 2023)](https://arxiv.org/abs/2201.12886)
- [MOIRAI-2: Unified Training of Universal Time Series Forecasting Transformers](https://arxiv.org/abs/2402.02592)
- [BuildingsBench: A Large-Scale Dataset for Building Load Forecasting](https://arxiv.org/abs/2307.00142)
- [Transfer Learning on Transformers for Building Energy Consumption](https://arxiv.org/abs/2410.14107)
- [Probabilistic Load Forecasting via Parallel CNN-BiGRU + Quantile Regression (2024)](https://www.researchgate.net/publication/381258042)
- [Conformalized Quantile Regression for Energy Forecasting](https://arxiv.org/abs/2510.15780)
- [Day-Ahead Net Load Forecasting for Renewable Integrated Buildings (MDPI 2025)](https://www.mdpi.com/1996-1073/18/6/1518)
- [Open-Meteo Free Weather API](https://open-meteo.com)
