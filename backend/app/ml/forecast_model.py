"""Shim — re-exports GRUForecastModel as ForecastModel for backwards compat."""

from app.ml.gru import GRUConfig as ForecastConfig, GRUForecastModel as ForecastModel

__all__ = ["ForecastConfig", "ForecastModel"]
