"""CSV data loader for energy load profiles."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pandas as pd


class TariffWindow(Enum):
    PEAK = "peak"        # 2PM - 10PM weekdays
    OFF_PEAK = "off_peak"  # 10PM - 2PM weekdays, weekends
    WEEKEND = "weekend"


@dataclass
class ScenarioMetadata:
    facility_name: str
    solar_installed_kwp: float | None
    tariff_type: str | None
    meter_type: str | None


class CSVLoader:
    """Loads and parses energy load profile CSV files."""

    def load(self, file_path: Path) -> pd.DataFrame:
        """Load a CSV file and return a normalized DataFrame."""
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        # Check which format: old (Date / End Time) or new (start_time)
        if "start_time" in first_line.lower():
            return self._load_new_format(file_path)
        else:
            return self._load_old_format(file_path)

    def _load_new_format(self, file_path: Path) -> pd.DataFrame:
        """Load new format CSV with start_time/end_time columns."""
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")
        df["start_time"] = pd.to_datetime(df["start_time"])
        df["end_time"] = pd.to_datetime(df["end_time"])
        df["datetime"] = df["start_time"]
        df = df.dropna(how="all")
        if "kw_import" not in df.columns:
            raise ValueError("CSV missing required 'kw_import' column")
        return df.sort_values("datetime").reset_index(drop=True)

    def _load_old_format(self, file_path: Path) -> pd.DataFrame:
        """Load old format CSV with 'Date / End Time' column, skipping metadata rows."""
        # Find the header row (contains "Date / End Time")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        header_idx = None
        for i, line in enumerate(lines):
            if "Date / End Time" in line:
                header_idx = i
                break

        if header_idx is None:
            raise ValueError(f"Could not find header in {file_path}")

        df = pd.read_csv(file_path, skiprows=header_idx)
        df.columns = df.columns.str.strip()

        # Normalize column names for consistent access
        col_map = {col: col.strip().lower().replace(" ", "_").replace("/", "_") for col in df.columns}
        df = df.rename(columns=col_map)

        # Parse datetime - try multiple formats
        datetime_col = "date__end_time" if "date__end_time" in df.columns else "date_end_time"
        if datetime_col not in df.columns:
            # Try original name
            datetime_col = [c for c in df.columns if "date" in c.lower() and "time" in c.lower()][0]

        df["datetime"] = pd.to_datetime(df[datetime_col], dayfirst=True, errors="coerce")
        if df["datetime"].isna().all():
            df["datetime"] = pd.to_datetime(df[datetime_col], yearfirst=True, errors="coerce")

        df = df.dropna(subset=["datetime"])
        if "kw_import" not in df.columns:
            raise ValueError("CSV missing required 'kw_import' column")

        return df.sort_values("datetime").reset_index(drop=True)

    def extract_metadata(self, file_path: Path) -> ScenarioMetadata:
        """Extract scenario metadata from CSV file headers."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:10]  # Read first 10 lines for metadata

        solar_kwp = None
        meter_type = None

        for line in lines:
            line_lower = line.lower()
            if "solar installed" in line_lower:
                import re
                match = re.search(r"(\d+\.?\d*)\s*[kK][wW][pP]?", line)
                if match:
                    solar_kwp = float(match.group(1))
            if "meter type" in line_lower:
                import re
                match = re.search(r"Meter Type,([^\n]+)", line, re.IGNORECASE)
                if match:
                    meter_type = match.group(1).strip()

        if solar_kwp is None:
            solar_kwp = 0.0

        filename = file_path.name
        if "SoL" in filename:
            facility = "SoL (Solar)"
        elif "Mi2" in filename:
            facility = "Mi2 (Solar)"
        elif "SuN" in filename:
            facility = "SuN (No Solar - Holiday)"
        elif "E.csv" in filename:
            facility = "E (No Solar - Weekday)"
        else:
            facility = file_path.stem

        return ScenarioMetadata(
            facility_name=facility,
            solar_installed_kwp=solar_kwp if solar_kwp > 0 else None,
            tariff_type=None,
            meter_type=meter_type,
        )
