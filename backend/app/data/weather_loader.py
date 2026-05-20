"""Fetch GHI (global horizontal irradiance) from Open-Meteo for a date range."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Kuala Lumpur — used for all facilities (best available approximation)
DEFAULT_LAT = 3.1390
DEFAULT_LON = 101.6869

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "weather_cache"


def fetch_ghi_historical(
    start_date: str,
    end_date: str,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    use_cache: bool = True,
) -> pd.Series:
    """Return 30-min GHI series (W/m²) for [start_date, end_date] (YYYY-MM-DD).

    Fetches hourly from Open-Meteo, forward-fills to 30-min intervals.
    Caches result as CSV to avoid repeated API calls.
    """
    cache_key = f"ghi_{lat}_{lon}_{start_date}_{end_date}.csv"
    cache_path = _CACHE_DIR / cache_key

    if use_cache and cache_path.exists():
        logger.info("weather | loading GHI from cache: %s", cache_key)
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        return df["ghi"]

    logger.info("weather | fetching GHI from Open-Meteo %s to %s", start_date, end_date)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "shortwave_radiation",
        "timezone": "Asia/Kuala_Lumpur",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    times = pd.to_datetime(data["hourly"]["time"])
    ghi = data["hourly"]["shortwave_radiation"]
    hourly = pd.Series(ghi, index=times, name="ghi", dtype="float32")

    # Upsample hourly -> 30-min via forward fill
    idx_30min = pd.date_range(hourly.index[0], hourly.index[-1], freq="30min")
    series = hourly.reindex(idx_30min).ffill().astype("float32")

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    series.to_frame().to_csv(cache_path)
    logger.info("weather | cached GHI to %s", cache_path)
    return series


def fetch_ghi_forecast(
    hours_ahead: int = 48,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
) -> pd.Series:
    """Return 30-min GHI forecast series for next `hours_ahead` hours."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "shortwave_radiation",
        "timezone": "Asia/Kuala_Lumpur",
        "forecast_days": max(1, (hours_ahead // 24) + 1),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    times = pd.to_datetime(data["hourly"]["time"])
    ghi = data["hourly"]["shortwave_radiation"]
    hourly = pd.Series(ghi, index=times, name="ghi", dtype="float32")

    now = pd.Timestamp.now(tz="Asia/Kuala_Lumpur").tz_localize(None)
    hourly = hourly[hourly.index >= now].iloc[:hours_ahead]

    idx_30min = pd.date_range(hourly.index[0], periods=len(hourly) * 2, freq="30min")
    series = hourly.reindex(idx_30min).ffill().dropna().astype("float32")
    return series


def align_ghi_to_df(df: pd.DataFrame, ghi: pd.Series) -> pd.Series:
    """Align GHI series to df['datetime'] index. Fills missing with 0."""
    ghi_aligned = ghi.reindex(df["datetime"].values).fillna(0.0).values
    return pd.Series(ghi_aligned, index=df.index, dtype="float32")
