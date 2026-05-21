"""Train GRU+Attention per facility and save separate weights."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.data.csv_loader import CSVLoader
from app.ml.gru_attention import GRUAttentionForecastModel

DATA_DIR = Path(__file__).parent / "data"
MODELS_DIR = Path(__file__).parent / "models"
EPOCHS = 30

FACILITIES = {
    "weekday":          "2. Load Profile (No Solar) E.csv",
    "holiday":          "3. Load Profile (No Solar) SuN.csv",
    "solar_duck_curve": "1. Load Profile (With Solar Installed) SoL.csv",
    "large_weekday":    "4. Load Profile (With Solar) Mi2.csv",
}

loader = CSVLoader()

for key, fname in FACILITIES.items():
    save_path = MODELS_DIR / f"gru_attention_{key}.pt"
    print(f"\n--- {key} ({fname[:45]}) ---")
    try:
        df = loader.load(DATA_DIR / fname)
        model = GRUAttentionForecastModel()
        print(f"device: {model.device}")
        X, y = model.prepare_sequence(df)
        print(f"sequences={len(X)}  shape={X.shape}")
        model.train_model(X, y, epochs=EPOCHS, verbose=True)
        model.save(save_path)
        print(f"saved -> {save_path}")
    except Exception as e:
        print(f"ERROR: {e}")
