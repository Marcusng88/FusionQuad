"""Train GRU+Attention on all 4 datasets and save weights."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from app.data.csv_loader import CSVLoader
from app.ml.gru_attention import GRUAttentionForecastModel

DATA_DIR = Path(__file__).parent / "data"
SAVE_PATH = Path(__file__).parent / "models" / "gru_attention_weights.pt"
EPOCHS = 30

FILES = [
    "1. Load Profile (With Solar Installed) SoL.csv",
    "2. Load Profile (No Solar) E.csv",
    "3. Load Profile (No Solar) SuN.csv",
    "4. Load Profile (With Solar) Mi2.csv",
]

loader = CSVLoader()
model = GRUAttentionForecastModel()
print(f"device: {model.device}")

Xs, ys = [], []
for fname in FILES:
    try:
        df = loader.load(DATA_DIR / fname)
        X, y = model.prepare_sequence(df)
        Xs.append(X)
        ys.append(y)
        print(f"loaded {fname[:40]}  sequences={len(X)}")
    except Exception as e:
        print(f"skip {fname[:40]}  {e}")

X_all = torch.cat(Xs)
y_all = torch.cat(ys)
print(f"\ntotal sequences={len(X_all)}  shape={X_all.shape}")

model.train_model(X_all, y_all, epochs=EPOCHS, verbose=True)
model.save(SAVE_PATH)
print(f"\nsaved -> {SAVE_PATH}")
