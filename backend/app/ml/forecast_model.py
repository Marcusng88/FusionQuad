"""GRU-based load forecasting model for energy management."""

from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np


@dataclass
class ForecastConfig:
    """Configuration for forecast model."""
    input_size: int = 1          # kw_import only
    hidden_size: int = 64        # GRU hidden size
    num_layers: int = 2          # number of GRU layers
    seq_len: int = 48            # 48 x 30min = 24 hours
    output_size: int = 1         # predict one step ahead
    dropout: float = 0.1


class _GRUModel(nn.Module):
    """GRU model that returns only the last output."""

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


class ForecastModel:
    """GRU-based load forecaster."""

    def __init__(self, config: ForecastConfig | None = None):
        self.config = config or ForecastConfig()
        self.model = _GRUModel(
            input_size=self.config.input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            dropout=self.config.dropout,
        )

    def prepare_sequence(self, df: pd.DataFrame) -> tuple[torch.Tensor, torch.Tensor]:
        """Convert DataFrame to sequence tensors for training.

        Creates sliding window sequences of seq_len from kw_import column.
        Returns X (samples, seq_len, 1) and y (samples,) target values.
        DataFrame is sorted by datetime ascending before creating sequences.
        All values are normalized to 0-1 range based on training data statistics.
        """
        if 'kw_import' not in df.columns:
            raise KeyError("DataFrame must have 'kw_import' column")

        # Sort by datetime ascending (data may be in reverse order)
        df = df.sort_values('datetime').reset_index(drop=True)

        values = df['kw_import'].values.astype(np.float32)
        seq_len = self.config.seq_len

        if len(values) < seq_len + 1:
            raise ValueError(
                f"DataFrame must have at least {seq_len + 1} rows, got {len(values)}"
            )

        # Normalize to 0-1 range for stable training
        self._min_val = values.min()
        self._max_val = values.max()
        if self._max_val > self._min_val:
            values = (values - self._min_val) / (self._max_val - self._min_val)

        X_list = []
        y_list = []

        for i in range(len(values) - seq_len):
            X_list.append(values[i:i + seq_len])
            y_list.append(values[i + seq_len])

        X = np.stack(X_list, axis=0).reshape(-1, seq_len, 1)
        y = np.stack(y_list, axis=0)

        return torch.from_numpy(X), torch.from_numpy(y)
        seq_len = self.config.seq_len

        if len(values) < seq_len + 1:
            raise ValueError(
                f"DataFrame must have at least {seq_len + 1} rows, got {len(values)}"
            )

        X_list = []
        y_list = []

        for i in range(len(values) - seq_len):
            X_list.append(values[i:i + seq_len])
            y_list.append(values[i + seq_len])

        X = np.stack(X_list, axis=0).reshape(-1, seq_len, 1)
        y = np.stack(y_list, axis=0)

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
        """Train the model on provided sequences."""
        dataset = TensorDataset(X, y)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()

        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0.0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                pred = self.model(batch_X).squeeze()
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            if verbose and (epoch + 1) % 5 == 0:
                avg_loss = epoch_loss / len(dataloader)
                print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict next load value given input sequence (denormalized)."""
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X).squeeze()
            # Denormalize if normalization was applied
            if hasattr(self, '_min_val') and hasattr(self, '_max_val'):
                scale = self._max_val - self._min_val
                if scale > 0:
                    pred = pred * scale + self._min_val
        return pred

    def evaluate_mape(self, X: torch.Tensor, y: torch.Tensor) -> float:
        """Calculate Mean Absolute Percentage Error on validation set.

        Predictions are denormalized before comparison with actual values.
        """
        self.model.eval()
        with torch.no_grad():
            pred = self.model(X).squeeze()
            y_actual = y.float()

            # Denormalize if normalization was applied
            if hasattr(self, '_min_val') and hasattr(self, '_max_val'):
                scale = self._max_val - self._min_val
                if scale > 0:
                    pred = pred * scale + self._min_val
                    y_actual = y_actual * scale + self._min_val

            # Avoid division by zero
            mask = y_actual != 0
            mape = torch.abs((pred[mask] - y_actual[mask]) / y_actual[mask]) * 100
            return mape.mean().item()

    def save(self, path: Path | str) -> None:
        """Save model weights to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            'model_state': self.model.state_dict(),
            'config': self.config,
            'min_val': getattr(self, '_min_val', None),
            'max_val': getattr(self, '_max_val', None),
        }, path)

    def load(self, path: Path | str) -> None:
        """Load model weights from file."""
        path = Path(path)
        checkpoint = torch.load(path, weights_only=False)
        self.model.load_state_dict(checkpoint['model_state'])
        if 'config' in checkpoint:
            self.config = checkpoint['config']
        if 'min_val' in checkpoint:
            self._min_val = checkpoint['min_val']
        if 'max_val' in checkpoint:
            self._max_val = checkpoint['max_val']