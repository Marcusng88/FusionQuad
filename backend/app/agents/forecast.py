"""Forecast agent - predicts rolling load using the GRU model."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import torch

from app.agents.state import AgentState, ForecastResult
from app.ml.forecast_model import ForecastModel

logger = logging.getLogger(__name__)


def forecast_node(state: AgentState) -> dict:
    """Generate rolling forecasts using only history available up to this tick."""
    model_path = Path(__file__).parent.parent.parent / "models" / "forecast_weights.pt"

    forecasts: dict[str, list[float]] = {}
    confidences: dict[str, float] = {}
    horizon = max(1, int(state.get("forecast_window") or 6))

    loaded = state.get("loaded_data") or {}
    current_index = state.get("current_record_index")

    for facility, payload in loaded.items():
        df = pd.DataFrame(payload["data"])
        if "datetime" not in df.columns or "kw_import" not in df.columns:
            continue

        df = df.sort_values("datetime").reset_index(drop=True)
        if len(df) < 49:
            forecasts[facility] = []
            confidences[facility] = 0.0
            continue

        model = ForecastModel()
        if model_path.exists():
            model.load(model_path)

        try:
            history = _historical_window(df, current_index, model.config.seq_len)
            confidence = _estimate_confidence(model, history)
            forecast_values = _predict_horizon(model, history, horizon)
            forecasts[facility] = forecast_values
            confidences[facility] = confidence
            logger.info(
                "forecast | facility=%s confidence=%.2f horizon=%d first_kw=%.1f",
                facility, confidence, horizon, forecast_values[0] if forecast_values else 0.0,
            )
        except Exception as exc:
            logger.warning("forecast | facility=%s failed: %s", facility, exc)
            forecasts[facility] = []
            confidences[facility] = 0.0

    return {
        "forecast": ForecastResult(
            load_forecast=forecasts,
            confidence=confidences,
            horizon=horizon,
        ),
        "messages": [
            {
                "role": "assistant",
                "content": f"Generated rolling forecasts for {len(forecasts)} facilities.",
            }
        ],
    }


def _historical_window(df: pd.DataFrame, current_index: int | None, seq_len: int) -> pd.DataFrame:
    if current_index is None:
        end_index = len(df) - 1
    else:
        end_index = max(seq_len, min(int(current_index), len(df) - 1))

    history = df.iloc[: end_index + 1].copy()
    if len(history) < seq_len + 1:
        raise ValueError("Not enough history for rolling forecast.")
    return history


def _estimate_confidence(model: ForecastModel, history: pd.DataFrame) -> float:
    X, y = model.prepare_sequence(history)
    n = len(X)
    if n <= 10:
        return 0.5

    split = max(1, int(0.8 * n))
    X_val = X[split:]
    y_val = y[split:]
    if len(X_val) == 0:
        return 0.5

    mape = model.evaluate_mape(X_val, y_val)
    if mape <= 5:
        return 0.95
    if mape <= 15:
        return 0.80
    if mape <= 30:
        return 0.60
    return 0.40


def _predict_horizon(model: ForecastModel, history: pd.DataFrame, horizon: int) -> list[float]:
    X, _ = model.prepare_sequence(history)
    seq = X[-1:].clone()
    scale = getattr(model, "_max_val", 0.0) - getattr(model, "_min_val", 0.0)

    predictions: list[float] = []
    for _ in range(horizon):
        with torch.no_grad():
            normalized = model.model(seq).reshape(-1)[0]

        denormalized = normalized
        if scale > 0:
            denormalized = normalized * scale + getattr(model, "_min_val", 0.0)

        value = float(denormalized.item())
        predictions.append(value)

        next_norm = normalized.reshape(1, 1, 1)
        seq = torch.cat([seq[:, 1:, :], next_norm], dim=1)

    return predictions
