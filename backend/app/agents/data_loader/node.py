"""DataLoader agent - loads CSV energy profile data for facility scenarios."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.data.csv_loader import CSVLoader

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

DEFAULT_MD_LIMIT_KW = 800.0


def _get_csv_filename(day_type: str) -> str:
    """Map day_type to CSV filename."""
    mapping = {
        "weekday": "2. Load Profile (No Solar) E.csv",
        "holiday": "3. Load Profile (No Solar) SuN.csv",
        "solar_duck_curve": "1. Load Profile (With Solar Installed) SoL.csv",
        "large_weekday": "4. Load Profile (With Solar) Mi2.csv",
    }
    if day_type not in mapping:
        logger.warning("Unknown day_type '%s', defaulting to weekday", day_type)
        day_type = "weekday"
    return mapping[day_type]


def load_facility_data(day_type: str) -> dict[str, Any]:
    """Load facility data for the given day type.

    Args:
        day_type: One of "weekday", "holiday", or "solar_duck_curve".

    Returns:
        Dict with "data" (DataFrame as dict) and "metadata" (ScenarioMetadata).
    """
    filename = _get_csv_filename(day_type)
    file_path = DATA_DIR / filename

    loader = CSVLoader()
    df = loader.load(file_path)
    metadata = loader.extract_metadata(file_path)

    solar_kwp = metadata.solar_installed_kwp or 0.0
    data_quality = {
        "rows": len(df),
        "missing_kw_import": int(df["kw_import"].isna().sum()) if "kw_import" in df.columns else 0,
        "solar_kwp": solar_kwp,
        "facility_name": metadata.facility_name,
    }

    datetime_col = df["datetime"]
    available_start = datetime_col.min().to_pydatetime()
    available_end = datetime_col.max().to_pydatetime()
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "data": df.to_dict(orient="records"),
        "metadata": {
            "solar_installed_kwp": solar_kwp,
            "facility_name": metadata.facility_name,
            "tariff_type": metadata.tariff_type,
            "meter_type": metadata.meter_type,
            "available_start": available_start,
            "available_end": available_end,
        },
        "data_quality": data_quality,
    }


def data_loader_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node that loads CSV data based on day_type.

    Args:
        state: Agent state containing day_type.

    Returns:
        Partial state update with loaded_data, data_quality, current_facility, md_limit_kw.
    """
    day_type = state.get("day_type", "weekday")

    if day_type not in ("weekday", "holiday", "solar_duck_curve", "large_weekday"):
        logger.warning("Unknown day_type '%s', defaulting to weekday", day_type)
        day_type = "weekday"

    result = load_facility_data(day_type)

    facility_key = day_type
    loaded_data = {facility_key: result}

    data_quality = {facility_key: result["data_quality"]}

    return {
        "loaded_data": loaded_data,
        "data_quality": data_quality,
        "current_facility": facility_key,
        "md_limit_kw": DEFAULT_MD_LIMIT_KW,
    }