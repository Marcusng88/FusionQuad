"""Train GRU+Attention with GHI weather feature for solar facilities (SoL, Mi2)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.data.csv_loader import CSVLoader
from app.data.weather_loader import fetch_ghi_historical, align_ghi_to_df
from app.ml.gru_attention import GRUAttentionForecastModel, GRUAttentionConfig

DATA_DIR = Path(__file__).parent / "data"
MODELS_DIR = Path(__file__).parent / "models"
EPOCHS = 30

# Solar facilities only — date ranges from CSVLoader output
SOLAR_FACILITIES = {
    "solar_duck_curve": {
        "csv": "1. Load Profile (With Solar Installed) SoL.csv",
        "start": "2025-09-01",
        "end":   "2025-09-30",
    },
    "large_weekday": {
        "csv": "4. Load Profile (With Solar) Mi2.csv",
        "start": "2025-11-01",
        "end":   "2026-01-01",
    },
}

loader = CSVLoader()

for key, info in SOLAR_FACILITIES.items():
    save_path = MODELS_DIR / f"gru_attention_{key}.pt"
    print(f"\n--- {key} ({info['csv'][:45]}) ---")
    try:
        df = loader.load(DATA_DIR / info["csv"])

        # Fetch GHI and align to load profile timestamps
        ghi_series = fetch_ghi_historical(info["start"], info["end"])
        ghi_aligned = align_ghi_to_df(df, ghi_series)

        # Normalize GHI to [0, 1] range (max ~1200 W/m2 tropical)
        ghi_max = float(ghi_aligned.max()) or 1200.0
        ghi_norm = (ghi_aligned.values / ghi_max).astype("float32")

        # Build model with input_size=12
        config = GRUAttentionConfig(input_size=12)
        model = GRUAttentionForecastModel(config)
        model._ghi_max = ghi_max  # persisted in checkpoint for inference
        print(f"device: {model.device}  input_size=12 (11 base + GHI)")

        X, y = model.prepare_sequence(df, ghi=ghi_norm)
        print(f"sequences={len(X)}  shape={X.shape}")

        model.train_model(X, y, epochs=EPOCHS, verbose=True)
        model.save(save_path)
        print(f"saved -> {save_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
