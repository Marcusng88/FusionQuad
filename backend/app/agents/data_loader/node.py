"""DataLoader agent - loads CSV energy profile data for facility scenarios."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

DEFAULT_MD_LIMIT_KW = 800.0


@dataclass
class ScenarioMetadata:
    """Metadata extracted from a scenario CSV file."""

    solar_kwp: float
    facility_name: str
    meter_type: str | None = None


class CSVLoader:
    """Loads and parses energy profile CSV files."""

    def load(self, file_path: Path) -> pd.DataFrame:
        """Load CSV file and return DataFrame.

        Args:
            file_path: Path to CSV file.

        Returns:
            DataFrame with datetime, kw_import, and optionally kw_solar columns.

        Raises:
            FileNotFoundError: If CSV file does not exist.
            ValueError: If kw_import column is missing.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        df = pd.read_csv(file_path)

        if "kw_import" not in df.columns:
            raise ValueError("CSV missing required 'kw_import' column")

        df = df.dropna(how="all")

        return df

    def extract_metadata(self, file_path: Path) -> ScenarioMetadata:
        """Extract metadata from CSV filename and content.

        Args:
            file_path: Path to CSV file.

        Returns:
            ScenarioMetadata with solar_kwp, facility_name, and meter_type.
        """
        filename = file_path.name.lower()

        solar_kwp = 0.0
        if "sol" in filename or "with solar" in filename:
            solar_kwp = 100.0

        facility_name = "Unknown Facility"
        if "e." in filename or "no solar" in filename:
            facility_name = "Weekday No Solar"
        elif "sun" in filename or "holiday" in filename:
            facility_name = "Holiday No Solar"
        elif "sol" in filename or "solar" in filename:
            facility_name = "Solar Duck Curve"

        meter_type = None
        if "mi2" in filename:
            meter_type = "MI2"

        return ScenarioMetadata(
            solar_kwp=solar_kwp,
            facility_name=facility_name,
            meter_type=meter_type,
        )


def _get_csv_filename(day_type: str) -> str:
    """Map day_type to CSV filename."""
    mapping = {
        "weekday": "2. Load Profile (No Solar) E.csv",
        "holiday": "3. Load Profile (No Solar) SuN.csv",
        "solar_duck_curve": "1. Load Profile (With Solar Installed) SoL.csv",
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

    data_quality = {
        "rows": len(df),
        "missing_kw_import": int(df["kw_import"].isna().sum()) if "kw_import" in df.columns else 0,
        "solar_kwp": metadata.solar_kwp,
        "facility_name": metadata.facility_name,
    }

    return {
        "data": df.to_dict(orient="records"),
        "metadata": {
            "solar_kwp": metadata.solar_kwp,
            "facility_name": metadata.facility_name,
            "meter_type": metadata.meter_type,
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

    if day_type not in ("weekday", "holiday", "solar_duck_curve"):
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