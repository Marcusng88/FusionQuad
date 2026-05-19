"""Retrain Mi2 (large_weekday) with 11 features — no GHI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.data.csv_loader import CSVLoader
from app.ml.gru_attention import GRUAttentionForecastModel

loader = CSVLoader()
df = loader.load(Path(__file__).parent / "data" / "4. Load Profile (With Solar) Mi2.csv")
model = GRUAttentionForecastModel()
print(f"device: {model.device}")
X, y = model.prepare_sequence(df)
print(f"sequences={len(X)}")
model.train_model(X, y, epochs=30, verbose=True)
model.save(Path(__file__).parent / "models" / "gru_attention_large_weekday.pt")
print("saved -> models/gru_attention_large_weekday.pt")
