"""Chronos zero-shot forecaster wrapper — same interface as GRU models."""

from pathlib import Path

import numpy as np
import pandas as pd
import torch


class ChronosForecastModel:
    """
    Zero-shot wrapper around Amazon Chronos-T5.
    No training required — uses pretrained weights.
    Matches evaluate_mape / prepare_sequence interface of GRU models.
    """

    MODEL_ID = "amazon/chronos-t5-small"  # 46MB, CPU-friendly

    def __init__(self, model_id: str | None = None, num_samples: int = 20):
        self.model_id = model_id or self.MODEL_ID
        self.num_samples = num_samples
        self._pipeline = None
        self._horizon = 6    # match GRUAttention default
        self._seq_len = 48   # context window fed to Chronos

    def _load_pipeline(self):
        if self._pipeline is not None:
            return
        try:
            from chronos import ChronosPipeline
        except ImportError as e:
            raise ImportError(
                "chronos-forecasting not installed. "
                "Run: uv add chronos-forecasting"
            ) from e

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._pipeline = ChronosPipeline.from_pretrained(
            self.model_id,
            device_map=device,
            dtype=torch.float32,
        )
        print(f"[Chronos] Loaded {self.model_id} on {device}")

    # ------------------------------------------------------------------
    # Compat interface (mirrors GRUAttentionForecastModel)
    # ------------------------------------------------------------------

    def prepare_sequence(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns (contexts, targets) as numpy arrays.
        contexts: (n, seq_len) — raw kw_import windows (NOT normalized)
        targets:  (n, horizon) — corresponding next-horizon kw_import values
        """
        if "kw_import" not in df.columns:
            raise KeyError("DataFrame must have 'kw_import' column")
        df = df.sort_values("datetime").reset_index(drop=True)
        values = df["kw_import"].values.astype(np.float32)

        seq_len = self._seq_len
        horizon = self._horizon

        if len(values) < seq_len + horizon:
            raise ValueError(f"Need at least {seq_len + horizon} rows, got {len(values)}")

        contexts, targets = [], []
        for i in range(len(values) - seq_len - horizon + 1):
            contexts.append(values[i : i + seq_len])
            targets.append(values[i + seq_len : i + seq_len + horizon])

        return np.stack(contexts), np.stack(targets)

    def evaluate_mape(self, contexts: np.ndarray, targets: np.ndarray) -> float:
        """
        MAPE on first horizon step across all validation windows.
        contexts: (n, seq_len)  targets: (n, horizon)
        """
        self._load_pipeline()

        preds_first_step = []
        actuals_first_step = []

        # Batch inference — feed each context window, take median of samples
        context_tensors = [
            torch.tensor(ctx, dtype=torch.float32) for ctx in contexts
        ]

        # Chronos accepts list of 1-D tensors (context is positional)
        forecast = self._pipeline.predict(
            context_tensors,
            self._horizon,
            num_samples=self.num_samples,
        )
        # forecast shape: (n, num_samples, horizon)
        median_forecast = np.median(forecast.numpy(), axis=1)  # (n, horizon)

        pred_step1 = median_forecast[:, 0]        # first horizon step
        actual_step1 = targets[:, 0]

        mask = actual_step1 != 0
        mape = np.abs((pred_step1[mask] - actual_step1[mask]) / actual_step1[mask]) * 100
        return float(mape.mean())

    def predict_horizon(self, df: pd.DataFrame, horizon: int) -> list[float]:
        """Single-shot multi-step forecast from last seq_len values in df."""
        self._load_pipeline()
        df = df.sort_values("datetime").reset_index(drop=True)
        values = df["kw_import"].values.astype(np.float32)
        context = torch.tensor(values[-self._seq_len :], dtype=torch.float32)

        forecast = self._pipeline.predict(
            [context],
            horizon,
            num_samples=self.num_samples,
        )
        # forecast: (1, num_samples, horizon)
        median = np.median(forecast.numpy(), axis=1)[0]  # (horizon,)
        return median[:horizon].tolist()

    def predict_quantiles(
        self, df: pd.DataFrame, horizon: int, quantiles: list[float] = [0.1, 0.5, 0.9]
    ) -> dict[str, list[float]]:
        """Return q10/q50/q90 forecast — Chronos native probabilistic output."""
        self._load_pipeline()
        df = df.sort_values("datetime").reset_index(drop=True)
        values = df["kw_import"].values.astype(np.float32)
        context = torch.tensor(values[-self._seq_len :], dtype=torch.float32)

        forecast = self._pipeline.predict(
            [context],
            horizon,
            num_samples=self.num_samples,
        )
        samples = forecast.numpy()[0]  # (num_samples, horizon)
        result = {}
        for q in quantiles:
            key = f"q{int(q*100)}"
            result[key] = np.quantile(samples, q, axis=0)[:horizon].tolist()
        return result

    # No-op save/load — zero-shot model, nothing to persist
    def save(self, path: Path | str) -> None:
        print(f"[Chronos] Zero-shot model — no weights to save.")

    def load(self, path: Path | str) -> None:
        print(f"[Chronos] Zero-shot model — weights loaded from HuggingFace on first predict.")
