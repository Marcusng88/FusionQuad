"""Forecast agent - predicts load using GRU model."""

from pathlib import Path

import pandas as pd
import torch

from app.agents.state import AgentState
from app.ml.forecast_model import ForecastModel


def forecast_node(state: AgentState) -> dict:
    """Generate load forecasts using GRU model.

    Uses the trained ForecastModel to predict load for loaded facility data.
    """
    model_path = Path(__file__).parent.parent.parent / "models" / "forecast_weights.pt"

    forecasts = {}
    confidences = {}

    loaded = state.get("loaded_data") or {}
    for facility, payload in loaded.items():
        df = pd.DataFrame(payload["data"])
        if "datetime" not in df.columns or "kw_import" not in df.columns:
            continue

        model = ForecastModel()

        # Load pre-trained weights if available
        if model_path.exists():
            model.load(model_path)

        try:
            X, y = model.prepare_sequence(df)

            # Use last 20% as validation signal
            n = len(X)
            if n > 10:
                split = max(1, int(0.8 * n))
                X_val = X[split:]
                y_val = y[split:]

                if len(X_val) > 0:
                    mape = model.evaluate_mape(X_val, y_val)
                    if mape <= 5:
                        confidence = 0.95
                    elif mape <= 15:
                        confidence = 0.80
                    elif mape <= 30:
                        confidence = 0.60
                    else:
                        confidence = 0.40
                else:
                    confidence = 0.5
            else:
                confidence = 0.5

            # Simple forecast: predict next step
            model.model.eval()
            with torch.no_grad():
                X_sample = X[-1:]
                pred = model.predict(X_sample)
                forecast_values = pred.cpu().tolist()
                if isinstance(forecast_values, (int, float)):
                    forecast_values = [forecast_values]

            forecasts[facility] = forecast_values
            confidences[facility] = confidence

        except Exception:
            forecasts[facility] = []
            confidences[facility] = 0.0

    return {
        "load_forecast": forecasts,
        "forecast_confidence": confidences,
        "messages": [
            {
                "role": "assistant",
                "content": f"Generated forecasts for {len(forecasts)} facilities.",
            }
        ],
    }