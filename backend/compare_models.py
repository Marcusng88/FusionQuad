"""Compare GRU vs GRU+Attention (lag+quantile) vs Chronos (zero-shot) on all 4 datasets."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from app.data.csv_loader import CSVLoader
from app.ml.gru import GRUForecastModel
from app.ml.gru_attention import GRUAttentionForecastModel

DATA_DIR = Path(__file__).parent / "data"
MODELS_DIR = Path(__file__).parent / "models"
GRU_WEIGHTS = MODELS_DIR / "gru_weights.pt"
ATTN_WEIGHTS = MODELS_DIR / "gru_attention_weights.pt"  # pooled fallback
SPLIT = 0.8

# Map CSV filename -> facility key (matches train_gru_attention.py and forecast.py)
FACILITY_KEYS = {
    "1. Load Profile (With Solar Installed) SoL.csv": "solar_duck_curve",
    "2. Load Profile (No Solar) E.csv":               "weekday",
    "3. Load Profile (No Solar) SuN.csv":             "holiday",
    "4. Load Profile (With Solar) Mi2.csv":           "large_weekday",
}

FILES = list(FACILITY_KEYS.keys())

# ---------------------------------------------------------------------------
# Check trained model weights exist
# ---------------------------------------------------------------------------
if not GRU_WEIGHTS.exists():
    print(f"Missing {GRU_WEIGHTS} -- run: python train_gru.py")
    sys.exit(1)

# Check at least one attention weights file exists
attn_files = list(MODELS_DIR.glob("gru_attention_*.pt")) + ([ATTN_WEIGHTS] if ATTN_WEIGHTS.exists() else [])
if not attn_files:
    print("Missing GRU+Attention weights -- run: python train_gru_attention.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Check Chronos availability
# ---------------------------------------------------------------------------
try:
    from app.ml.chronos_model import ChronosForecastModel
    chronos_available = True
except ImportError:
    chronos_available = False

loader = CSVLoader()

print(f"\n{'Dataset':<22} {'Model':<26} {'MAPE %':>8} {'Q-spread':>9} {'Val seqs':>9}")
print("-" * 80)

for fname in FILES:
    label = fname[:20]
    try:
        df = loader.load(DATA_DIR / fname)
    except Exception as e:
        print(f"{label:<22} ERROR loading: {e}")
        continue

    # -----------------------------------------------------------------------
    # GRU (baseline)
    # -----------------------------------------------------------------------
    try:
        gru = GRUForecastModel()
        gru.load(GRU_WEIGHTS)
        X, y = gru.prepare_sequence(df)
        split = int(SPLIT * len(X))
        mape = gru.evaluate_mape(X[split:], y[split:])
        print(f"{label:<22} {'GRU':<26} {mape:>8.2f} {'n/a':>9} {len(X)-split:>9}")
    except Exception as e:
        print(f"{label:<22} {'GRU':<26} {'ERROR':>8}  {e}")

    # -----------------------------------------------------------------------
    # GRU + Attention + Lag + Quantile (Phase 1 — facility-specific weights)
    # -----------------------------------------------------------------------
    try:
        attn = GRUAttentionForecastModel()
        fkey = FACILITY_KEYS.get(fname)
        specific = MODELS_DIR / f"gru_attention_{fkey}.pt" if fkey else None
        weights = specific if (specific and specific.exists()) else ATTN_WEIGHTS
        attn.load(weights)
        X2, y2 = attn.prepare_sequence(df)
        split2 = int(SPLIT * len(X2))
        X_val, y_val = X2[split2:], y2[split2:]
        mape2 = attn.evaluate_mape(X_val, y_val)
        # compute q90 - q10 spread (avg over val set, first horizon step)
        q_preds = attn.predict_quantiles(X_val)
        spread = (q_preds["q90"][:, 0] - q_preds["q10"][:, 0]).mean().item()
        tag = "GRU+Attn+Fac" if (specific and specific.exists()) else "GRU+Attn+Lag+Q"
        print(f"{label:<22} {tag:<26} {mape2:>8.2f} {spread:>9.1f} {len(X2)-split2:>9}")
    except Exception as e:
        print(f"{label:<22} {'GRU+Attn+Lag+Q':<26} {'ERROR':>8}  {e}")

    # -----------------------------------------------------------------------
    # Chronos (zero-shot, no training)
    # -----------------------------------------------------------------------
    # if chronos_available:
    #     try:
    #         chronos = ChronosForecastModel()
    #         contexts, targets = chronos.prepare_sequence(df)
    #         split3 = int(SPLIT * len(contexts))
    #         print(f"{label:<22} {'Chronos (zero-shot)':<26} ", end="", flush=True)
    #         mape3 = chronos.evaluate_mape(contexts[split3:], targets[split3:])
    #         print(f"{mape3:>8.2f} {'n/a':>9} {len(contexts)-split3:>9}")
    #     except Exception as e:
    #         print(f"{label:<22} {'Chronos (zero-shot)':<26} {'ERROR':>8}  {e}")
    # else:
    #     print(f"{label:<22} {'Chronos (zero-shot)':<26} {'SKIP — not installed':>30}")

    # print()

print("-" * 80)
if not chronos_available:
    print("\nTo enable Chronos: uv add chronos-forecasting")
    print("Then re-run: python compare_models.py")
