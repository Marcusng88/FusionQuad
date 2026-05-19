"""Compare GRU vs GRU+Attention (lag+quantile) vs Chronos (zero-shot) on all 4 datasets."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from app.data.csv_loader import CSVLoader
from app.ml.gru import GRUForecastModel
from app.ml.gru_attention import GRUAttentionForecastModel

DATA_DIR = Path(__file__).parent / "data"
GRU_WEIGHTS = Path(__file__).parent / "models" / "gru_weights.pt"
ATTN_WEIGHTS = Path(__file__).parent / "models" / "gru_attention_weights.pt"
SPLIT = 0.8

FILES = [
    "1. Load Profile (With Solar Installed) SoL.csv",
    "2. Load Profile (No Solar) E.csv",
    "3. Load Profile (No Solar) SuN.csv",
    "4. Load Profile (With Solar) Mi2.csv",
]

# ---------------------------------------------------------------------------
# Check trained model weights exist
# ---------------------------------------------------------------------------
if not GRU_WEIGHTS.exists():
    print(f"Missing {GRU_WEIGHTS} — run: python train_gru.py")
    sys.exit(1)
if not ATTN_WEIGHTS.exists():
    print(f"Missing {ATTN_WEIGHTS} — run: python train_gru_attention.py")
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
    # GRU + Attention + Lag + Quantile (Phase 1)
    # -----------------------------------------------------------------------
    try:
        attn = GRUAttentionForecastModel()
        attn.load(ATTN_WEIGHTS)
        X2, y2 = attn.prepare_sequence(df)
        split2 = int(SPLIT * len(X2))
        X_val, y_val = X2[split2:], y2[split2:]
        mape2 = attn.evaluate_mape(X_val, y_val)
        # compute q90 - q10 spread (avg over val set, first horizon step)
        q_preds = attn.predict_quantiles(X_val)
        spread = (q_preds["q90"][:, 0] - q_preds["q10"][:, 0]).mean().item()
        print(f"{label:<22} {'GRU+Attn+Lag+Q':<26} {mape2:>8.2f} {spread:>9.1f} {len(X2)-split2:>9}")
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
