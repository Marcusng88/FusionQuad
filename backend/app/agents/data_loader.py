"""DataLoader agent - loads and validates CSV energy data."""

from pathlib import Path

import pandas as pd

from app.agents.state import AgentState
from app.data.csv_loader import CSVLoader


def data_loader_node(state: AgentState) -> dict:
    """Load energy profile CSV files and validate data quality.

    Reads CSV files from the data directory and produces data quality metrics.
    """
    loader = CSVLoader()
    data_dir = Path(__file__).parent.parent.parent / "data"

    results = {}
    quality_metrics = {}

    csv_files = list(data_dir.glob("*.csv"))
    for file_path in csv_files:
        facility = file_path.stem
        df = loader.load(file_path)
        metadata = loader.extract_metadata(file_path)

        # Basic data quality checks
        missing_kw = df["kw_import"].isna().sum() if "kw_import" in df.columns else len(df)
        quality_metrics[facility] = {
            "rows": len(df),
            "missing_kw_import": int(missing_kw),
            "solar_kwp": metadata.solar_installed_kwp,
            "facility": metadata.facility_name,
        }
        results[facility] = {
            "data": df.to_dict(),
            "metadata": {
                "facility_name": metadata.facility_name,
                "solar_installed_kwp": metadata.solar_installed_kwp,
                "tariff_type": metadata.tariff_type,
                "meter_type": metadata.meter_type,
            },
        }

    return {
        "loaded_data": results,
        "data_quality": quality_metrics,
        "messages": [
            {
                "role": "assistant",
                "content": f"Loaded {len(csv_files)} facility datasets. Data quality checked.",
            }
        ],
    }