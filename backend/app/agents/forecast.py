"""Forecast agent - predicts rolling load using GRU or GRU+Attention model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.agents.state import AgentState, ForecastResult

logger = logging.getLogger(__name__)

_MODELS_DIR = Path(__file__).parent.parent.parent / "models"

_MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "gru_attention": {
        "weights": _MODELS_DIR / "gru_attention_weights.pt",
        "cls": None,  # lazy import
    },
    "gru": {
        "weights": _MODELS_DIR / "gru_weights.pt",
        "cls": None,
    },
}

_MODEL_CACHE: dict[str, Any] = {}


def _get_model(model_name: str) -> Any:
    """Return cached model instance for model_name, loading on first call."""
    name = model_name if model_name in _MODEL_CONFIGS else "gru_attention"
    if name in _MODEL_CACHE:
        return _MODEL_CACHE[name]

    cfg = _MODEL_CONFIGS[name]
    if name == "gru_attention":
        from app.ml.gru_attention import GRUAttentionForecastModel
        model = GRUAttentionForecastModel()
    else:
        from app.ml.gru import GRUForecastModel
        model = GRUForecastModel()

    weights_path: Path = cfg["weights"]
    if weights_path.exists():
        model.load(weights_path)
        logger.info("forecast | loaded model=%s weights=%s", name, weights_path.name)
    else:
        logger.critical("forecast | weights not found at %s — predictions are random", weights_path)

    _MODEL_CACHE[name] = model
    return model


def forecast_node(state: AgentState) -> dict:
    """Generate rolling forecasts using only history available up to this tick."""
    model_name: str = state.get("forecast_model") or "gru_attention"
    model = _get_model(model_name)

    forecasts: dict[str, list[float]] = {}
    confidences: dict[str, float] = {}
    horizon = max(1, int(state.get("forecast_window") or 6))

    loaded = state.get("loaded_data") or {}
    current_index = state.get("current_record_index")

    for facility, payload in loaded.items():
        df = pd.DataFrame(payload["data"])
        if "datetime" not in df.columns or "kw_import" not in df.columns:
            continue

        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)
        if len(df) < 49:
            forecasts[facility] = []
            confidences[facility] = 0.0
            continue

        try:
            history = _historical_window(df, current_index, model.config.seq_len)
            confidence = _estimate_confidence(model, history)
            forecast_values = model.predict_horizon(history, horizon)
            forecasts[facility] = forecast_values
            confidences[facility] = confidence
            logger.info(
                "forecast | facility=%s model=%s confidence=%.2f horizon=%d first_kw=%.1f",
                facility, model_name, confidence, horizon,
                forecast_values[0] if forecast_values else 0.0,
            )
        except Exception as exc:
            logger.warning("forecast | facility=%s model=%s failed: %s", facility, model_name, exc)
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
                "content": f"Generated rolling forecasts for {len(forecasts)} facilities using {model_name}.",
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


def _estimate_confidence(model: Any, history: pd.DataFrame) -> float:
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
