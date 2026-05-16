"""Compare saved GRU vs GRU+Attention weights on all 4 datasets."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

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

if not GRU_WEIGHTS.exists():
    print(f"Missing {GRU_WEIGHTS} — run: python train_gru.py")
    sys.exit(1)
if not ATTN_WEIGHTS.exists():
    print(f"Missing {ATTN_WEIGHTS} — run: python train_gru_attention.py")
    sys.exit(1)

loader = CSVLoader()

print(f"\n{'Dataset':<22} {'Model':<16} {'MAPE %':>8} {'Val seqs':>9}")
print("-" * 60)

for fname in FILES:
    label = fname[:20]
    try:
        df = loader.load(DATA_DIR / fname)
    except Exception as e:
        print(f"{label:<22} ERROR loading: {e}")
        continue

    # GRU
    try:
        gru = GRUForecastModel()
        gru.load(GRU_WEIGHTS)
        X, y = gru.prepare_sequence(df)
        split = int(SPLIT * len(X))
        mape = gru.evaluate_mape(X[split:], y[split:])
        print(f"{label:<22} {'GRU':<16} {mape:>8.2f} {len(X)-split:>9}")
    except Exception as e:
        print(f"{label:<22} {'GRU':<16} {'ERROR':>8}  {e}")

    # GRU + Attention
    try:
        attn = GRUAttentionForecastModel()
        attn.load(ATTN_WEIGHTS)
        X2, y2 = attn.prepare_sequence(df)
        split2 = int(SPLIT * len(X2))
        mape2 = attn.evaluate_mape(X2[split2:], y2[split2:])
        print(f"{label:<22} {'GRU+Attention':<16} {mape2:>8.2f} {len(X2)-split2:>9}")
    except Exception as e:
        print(f"{label:<22} {'GRU+Attention':<16} {'ERROR':>8}  {e}")

    print()
