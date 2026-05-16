"""Baseline GRU load forecasting model (single-feature, autoregressive)."""

import dataclasses
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np


@dataclass
class GRUConfig:
    input_size: int = 1
    hidden_size: int = 64
    num_layers: int = 2
    seq_len: int = 48
    output_size: int = 1
    dropout: float = 0.1


class _GRUNet(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gru_out, _ = self.gru(x)
        return self.fc(gru_out[:, -1, :])


class GRUForecastModel:
    """Baseline GRU: single feature (kw_import), autoregressive multi-step."""

    def __init__(self, config: GRUConfig | None = None):
        self.config = config or GRUConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = _GRUNet(
            input_size=self.config.input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            dropout=self.config.dropout,
        ).to(self.device)

    def prepare_sequence(self, df: pd.DataFrame) -> tuple[torch.Tensor, torch.Tensor]:
        if "kw_import" not in df.columns:
            raise KeyError("DataFrame must have 'kw_import' column")
        df = df.sort_values("datetime").reset_index(drop=True)
        values = df["kw_import"].values.astype(np.float32)
        seq_len = self.config.seq_len
        if len(values) < seq_len + 1:
            raise ValueError(f"Need at least {seq_len + 1} rows, got {len(values)}")
        self._min_val = values.min()
        self._max_val = values.max()
        if self._max_val > self._min_val:
            values = (values - self._min_val) / (self._max_val - self._min_val)
        X_list, y_list = [], []
        for i in range(len(values) - seq_len):
            X_list.append(values[i : i + seq_len])
            y_list.append(values[i + seq_len])
        X = np.stack(X_list).reshape(-1, seq_len, 1)
        y = np.stack(y_list)
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
                pred = self.model(bx).squeeze()
                loss = criterion(pred, by)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            if verbose and (epoch + 1) % 5 == 0:
                print(f"[GRU] Epoch {epoch+1}/{epochs}  loss={epoch_loss/len(loader):.4f}")

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X.to(self.device)).squeeze()
            if hasattr(self, "_min_val") and hasattr(self, "_max_val"):
                scale = self._max_val - self._min_val
                if scale > 0:
                    pred = pred * scale + self._min_val
        return pred

    def predict_horizon(self, df: pd.DataFrame, horizon: int) -> list[float]:
        """Autoregressive multi-step forecast."""
        X, _ = self.prepare_sequence(df)
        seq = X[-1:].clone().to(self.device)
        scale = getattr(self, "_max_val", 0.0) - getattr(self, "_min_val", 0.0)
        self.model.eval()
        predictions: list[float] = []
        for _ in range(horizon):
            with torch.no_grad():
                norm = self.model(seq).reshape(-1)[0]
            value = float((norm * scale + self._min_val).item()) if scale > 0 else float(norm.item())
            predictions.append(value)
            seq = torch.cat([seq[:, 1:, :], norm.reshape(1, 1, 1)], dim=1)
        return predictions

    def evaluate_mape(self, X: torch.Tensor, y: torch.Tensor) -> float:
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X.to(self.device)).squeeze()
            y_actual = y.float().to(self.device)
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
        self.model.load_state_dict(checkpoint["model_state"])
        if "config" in checkpoint:
            self.config = GRUConfig(**checkpoint["config"])
        if checkpoint.get("min_val") is not None:
            self._min_val = checkpoint["min_val"]
        if checkpoint.get("max_val") is not None:
            self._max_val = checkpoint["max_val"]
