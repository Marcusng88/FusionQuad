"""Tests for DataLoader agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.data.csv_loader import CSVLoader, ScenarioMetadata
from app.agents.data_loader.node import data_loader_node, load_facility_data


class TestCSVLoader:
    """Tests for CSVLoader."""

    def test_load_parses_csv_correctly(self, tmp_path: Path) -> None:
        """CSVLoader.load returns DataFrame with datetime and kw_import columns."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,50.0
    2024-01-01 01:00:00,110.0,45.0
    """
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader()
        df = loader.load(csv_file)

        assert "datetime" in df.columns
        assert "kw_import" in df.columns
        assert len(df) == 2

    def test_load_raises_on_missing_kw_import(self, tmp_path: Path) -> None:
        """CSVLoader.load raises ValueError when kw_import column is missing."""
        csv_content = """Date / End Time,other_column
    2024-01-01 00:00:00,value
    """
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader()
        with pytest.raises(ValueError, match="kw_import"):
            loader.load(csv_file)

    def test_load_handles_empty_rows(self, tmp_path: Path) -> None:
        """CSVLoader.load skips rows that are all NaN."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,50.0
    ,,
    2024-01-01 01:00:00,110.0,45.0
    """
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader()
        df = loader.load(csv_file)

        assert len(df) == 2

    def test_load_raises_on_file_not_found(self) -> None:
        """CSVLoader.load raises FileNotFoundError for missing file."""
        loader = CSVLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(Path("/nonexistent/file.csv"))

    def test_extract_metadata_returns_scenario_metadata(self, tmp_path: Path) -> None:
        """CSVLoader.extract_metadata returns ScenarioMetadata with solar_kwp and facility_name."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,50.0
    """
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        loader = CSVLoader()
        metadata = loader.extract_metadata(csv_file)

        assert isinstance(metadata, ScenarioMetadata)
        assert metadata.facility_name is not None
        assert isinstance(metadata.solar_installed_kwp, float)


class TestLoadFacilityData:
    """Tests for load_facility_data function."""

    def test_loads_weekday_csv(self, tmp_path: Path, monkeypatch: Any) -> None:
        """load_facility_data loads weekday CSV when day_type is weekday."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    2024-01-01 01:00:00,110.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        result = load_facility_data("weekday")
        assert result is not None
        assert "data" in result
        assert "metadata" in result

    def test_loads_holiday_csv(self, tmp_path: Path, monkeypatch: Any) -> None:
        """load_facility_data loads holiday CSV when day_type is holiday."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "3. Load Profile (No Solar) SuN.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        result = load_facility_data("holiday")
        assert result is not None

    def test_loads_solar_duck_curve_csv(self, tmp_path: Path, monkeypatch: Any) -> None:
        """load_facility_data loads solar CSV when day_type is solar_duck_curve."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,50.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "1. Load Profile (With Solar Installed) SoL.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        result = load_facility_data("solar_duck_curve")
        assert result is not None

    def test_defaults_to_weekday_on_unknown_day_type(self, tmp_path: Path, monkeypatch: Any) -> None:
        """load_facility_data defaults to weekday and logs warning for unknown day_type."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        result = load_facility_data("unknown_day")
        assert result is not None


class TestDataLoaderNode:
    """Tests for data_loader_node function."""

    def test_node_writes_loaded_data_to_state(self, tmp_path: Path, monkeypatch: Any) -> None:
        """data_loader_node writes loaded_data to state."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        state: dict[str, Any] = {"day_type": "weekday", "loaded_data": None}
        result = data_loader_node(state)

        assert result["loaded_data"] is not None
        assert "weekday" in result["loaded_data"] or len(result["loaded_data"]) > 0

    def test_node_writes_data_quality_to_state(self, tmp_path: Path, monkeypatch: Any) -> None:
        """data_loader_node writes data_quality to state."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    2024-01-01 01:00:00,110.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        state: dict[str, Any] = {"day_type": "weekday", "data_quality": None}
        result = data_loader_node(state)

        assert result["data_quality"] is not None

    def test_node_writes_current_facility_to_state(self, tmp_path: Path, monkeypatch: Any) -> None:
        """data_loader_node writes current_facility to state based on day_type."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        state: dict[str, Any] = {"day_type": "weekday", "current_facility": None}
        result = data_loader_node(state)

        assert result["current_facility"] is not None

    def test_node_reads_day_type_from_state(self, tmp_path: Path, monkeypatch: Any) -> None:
        """data_loader_node uses day_type from incoming state."""
        csv_content = """Date / End Time,kw_import,kw_solar
    2024-01-01 00:00:00,100.0,0.0
    """
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "3. Load Profile (No Solar) SuN.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        state: dict[str, Any] = {"day_type": "holiday", "loaded_data": None}
        result = data_loader_node(state)

        assert result["current_facility"] is not None

    def test_node_sets_md_limit_kw(self, tmp_path: Path, monkeypatch: Any) -> None:
        """data_loader_node sets md_limit_kw to default 800 kW."""
        csv_content = """datetime,kw_import,kw_solar
2024-01-01 00:00:00,100.0,0.0
"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "2. Load Profile (No Solar) E.csv").write_text(csv_content)

        monkeypatch.setattr("app.agents.data_loader.node.DATA_DIR", data_dir)

        state: dict[str, Any] = {"day_type": "weekday", "md_limit_kw": None}
        result = data_loader_node(state)

        assert result["md_limit_kw"] == 800.0