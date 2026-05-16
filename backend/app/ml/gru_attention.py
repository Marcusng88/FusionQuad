"""GRU + Bahdanau Attention with time covariates — direct multi-step forecast."""

import dataclasses
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np


@dataclass
class GRUAttentionConfig:
    input_size: int = 6       # kw_import + hour_sin/cos + day_sin/cos + is_peak
    hidden_size: int = 64
    num_layers: int = 2
    seq_len: int = 48
    horizon: int = 6          # direct multi-step output
    dropout: float = 0.1


class _BahdanauAttention(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.W_query = nn.Linear(hidden_size, hidden_size, bias=False)
        self.W_key = nn.Linear(hidden_size, hidden_size, bias=False)
        self.v = nn.Linear(hidden_size, 1, bias=False)

    def forward(self, query: torch.Tensor, keys: torch.Tensor) -> torch.Tensor:
        # query: (batch, hidden)  keys: (batch, seq_len, hidden)
        q = self.W_query(query).unsqueeze(1)          # (batch, 1, hidden)
        k = self.W_key(keys)                           # (batch, seq_len, hidden)
        scores = self.v(torch.tanh(q + k)).squeeze(-1) # (batch, seq_len)
        weights = F.softmax(scores, dim=-1)            # (batch, seq_len)
        context = (weights.unsqueeze(-1) * keys).sum(dim=1)  # (batch, hidden)
        return context


class _GRUAttentionNet(nn.Module):
    def __init__(self, config: GRUAttentionConfig):
        super().__init__()
        self.gru = nn.GRU(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            batch_first=True,
            dropout=config.dropout if config.num_layers > 1 else 0,
        )
        self.attention = _BahdanauAttention(config.hidden_size)
        self.fc1 = nn.Linear(config.hidden_size * 2, config.hidden_size)
        self.fc2 = nn.Linear(config.hidden_size, config.horizon)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        gru_out, _ = self.gru(x)                        # (batch, seq_len, hidden)
        last = gru_out[:, -1, :]                        # (batch, hidden)
        context = self.attention(last, gru_out)         # (batch, hidden)
        combined = torch.cat([last, context], dim=-1)   # (batch, hidden*2)
        out = self.dropout(F.relu(self.fc1(combined)))  # (batch, hidden)
        return self.fc2(out)                            # (batch, horizon)


def _add_time_features(df: pd.DataFrame) -> np.ndarray:
    """Return (n, 6) array: normalized kw + hour_sin/cos + day_sin/cos + is_peak."""
    kw = df["kw_import"].values.astype(np.float32)
    hour = df["datetime"].dt.hour.values.astype(np.float32)
    dow = df["datetime"].dt.dayofweek.values.astype(np.float32)
    hour_sin = np.sin(2 * np.pi * hour / 24).astype(np.float32)
    hour_cos = np.cos(2 * np.pi * hour / 24).astype(np.float32)
    day_sin = np.sin(2 * np.pi * dow / 7).astype(np.float32)
    day_cos = np.cos(2 * np.pi * dow / 7).astype(np.float32)
    is_peak = ((hour >= 14) & (hour < 22) & (dow < 5)).astype(np.float32)
    return np.stack([kw, hour_sin, hour_cos, day_sin, day_cos, is_peak], axis=1)


class GRUAttentionForecastModel:
    """GRU + Bahdanau Attention: 6-feature input, direct horizon-step output."""

    def __init__(self, config: GRUAttentionConfig | None = None):
        self.config = config or GRUAttentionConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = _GRUAttentionNet(self.config).to(self.device)

    def prepare_sequence(self, df: pd.DataFrame) -> tuple[torch.Tensor, torch.Tensor]:
        if "kw_import" not in df.columns or "datetime" not in df.columns:
            raise KeyError("DataFrame must have 'kw_import' and 'datetime' columns")
        df = df.sort_values("datetime").reset_index(drop=True)
        features = _add_time_features(df)  # (n, 6)
        seq_len = self.config.seq_len
        horizon = self.config.horizon
        if len(features) < seq_len + horizon:
            raise ValueError(f"Need at least {seq_len + horizon} rows, got {len(features)}")

        # Normalize kw_import (column 0) only
        kw = features[:, 0]
        self._min_val = float(kw.min())
        self._max_val = float(kw.max())
        if self._max_val > self._min_val:
            features[:, 0] = (kw - self._min_val) / (self._max_val - self._min_val)

        X_list, y_list = [], []
        for i in range(len(features) - seq_len - horizon + 1):
            X_list.append(features[i : i + seq_len])
            # y = next `horizon` kw_import values (normalized)
            y_list.append(features[i + seq_len : i + seq_len + horizon, 0])

        X = np.stack(X_list).astype(np.float32)        # (n, seq_len, 6)
        y = np.stack(y_list).astype(np.float32)        # (n, horizon)
        return torch.from_numpy(X), torch.from_numpy(y)

    def train_model(
        self,
        X: torch.Tensor,
        y: torch.Tensor,
        epochs: int = 20,
        batch_size: int = 64,
        learning_rate: float = 0.001,
        verbose: bool = True,
    ) -> None:
        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0.0
            for bx, by in loader:
                bx, by = bx.to(self.device), by.to(self.device)
                optimizer.zero_grad()
                pred = self.model(bx)      # (batch, horizon)
                loss = criterion(pred, by)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            if verbose and (epoch + 1) % 5 == 0:
                print(f"[GRUAttention] Epoch {epoch+1}/{epochs}  loss={epoch_loss/len(loader):.4f}")

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Returns (batch, horizon) denormalized kw predictions."""
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X.to(self.device))   # (batch, horizon)
            if hasattr(self, "_min_val") and hasattr(self, "_max_val"):
                scale = self._max_val - self._min_val
                if scale > 0:
                    pred = pred * scale + self._min_val
        return pred

    def predict_horizon(self, df: pd.DataFrame, horizon: int) -> list[float]:
        """Single-shot multi-step forecast from last sequence in df."""
        X, _ = self.prepare_sequence(df)
        pred = self.predict(X[-1:])  # (1, horizon)
        steps = min(horizon, self.config.horizon)
        return pred[0, :steps].tolist()

    def evaluate_mape(self, X: torch.Tensor, y: torch.Tensor) -> float:
        """MAPE on first horizon step (for confidence compat with GRUForecastModel)."""
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X.to(self.device))[:, 0]   # first step only
            y_actual = (y[:, 0].float() if y.dim() == 2 else y.float()).to(self.device)
            if hasattr(self, "_min_val") and hasattr(self, "_max_val"):
                scale = self._max_val - self._min_val
                if scale > 0:
                    pred = pred * scale + self._min_val
                    y_actual = y_actual * scale + self._min_val
            mask = y_actual != 0
            mape = torch.abs((pred[mask] - y_actual[mask]) / y_actual[mask]) * 100
            return mape.mean().item()

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state": self.model.state_dict(),
            "config": dataclasses.asdict(self.config),
            "min_val": float(self._min_val) if hasattr(self, "_min_val") else None,
            "max_val": float(self._max_val) if hasattr(self, "_max_val") else None,
        }, path)

    def load(self, path: Path | str) -> None:
        checkpoint = torch.load(Path(path), weights_only=True, map_location=self.device)
        if "config" in checkpoint:
            self.config = GRUAttentionConfig(**checkpoint["config"])
            self.model = _GRUAttentionNet(self.config).to(self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        if checkpoint.get("min_val") is not None:
            self._min_val = checkpoint["min_val"]
        if checkpoint.get("max_val") is not None:
            self._max_val = checkpoint["max_val"]
