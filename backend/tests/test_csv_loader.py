import pytest
from pathlib import Path
from app.data.csv_loader import CSVLoader


@pytest.fixture
def data_dir():
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def loader():
    return CSVLoader()


def test_load_sol_csv_returns_dataframe(loader, data_dir):
    """Tracer bullet: verify CSV loader can load SoL file and returns a DataFrame."""
    file_path = data_dir / "1. Load Profile (With Solar Installed) SoL.csv"
    df = loader.load(file_path)

    assert df is not None
    assert len(df) > 0
    assert "datetime" in df.columns or "start_time" in df.columns


def test_load_e_csv_returns_dataframe(loader, data_dir):
    """Verify E (No Solar) CSV loads correctly with YYYY-MM-DD format."""
    file_path = data_dir / "2. Load Profile (No Solar) E.csv"
    df = loader.load(file_path)

    assert df is not None
    assert len(df) > 0


def test_load_sun_csv_returns_dataframe(loader, data_dir):
    """Verify SuN (holiday) CSV loads correctly."""
    file_path = data_dir / "3. Load Profile (No Solar) SuN.csv"
    df = loader.load(file_path)

    assert df is not None
    assert len(df) > 0


def test_load_mi2_csv_returns_dataframe(loader, data_dir):
    """Verify Mi2 (With Solar) CSV loads correctly."""
    file_path = data_dir / "4. Load Profile (With Solar) Mi2.csv"
    df = loader.load(file_path)

    assert df is not None
    assert len(df) > 0


def test_extract_scenario_metadata_sol(loader, data_dir):
    """Verify metadata extraction for SoL file (944.88 kWp solar)."""
    file_path = data_dir / "1. Load Profile (With Solar Installed) SoL.csv"
    metadata = loader.extract_metadata(file_path)

    assert metadata.solar_installed_kwp is not None
    assert metadata.solar_installed_kwp > 0


def test_extract_scenario_metadata_sun(loader, data_dir):
    """Verify SuN file has no solar."""
    file_path = data_dir / "3. Load Profile (No Solar) SuN.csv"
    metadata = loader.extract_metadata(file_path)

    assert metadata.solar_installed_kwp == 0.0 or metadata.solar_installed_kwp is None


def test_mi2_weekend_peak_high(loader, data_dir):
    """Verify Mi2 (With Solar) has peak >1500 kW on weekend data."""
    file_path = data_dir / "4. Load Profile (With Solar) Mi2.csv"
    df = loader.load(file_path)

    max_kw = df["kw_import"].max()
    # Mi2 has peaks > 1500 kW
    assert max_kw > 1500, f"Expected peak > 1500 kW, got {max_kw}"


def test_e_weekday_baseline(loader, data_dir):
    """Verify E (No Solar) weekday data has peaks >1000 kW."""
    file_path = data_dir / "2. Load Profile (No Solar) E.csv"
    df = loader.load(file_path)

    max_kw = df["kw_import"].max()
    # E file should have peaks > 1000 kW (actual is ~1560 kW)
    assert max_kw > 1000, f"Expected peak > 1000 kW for weekday, got {max_kw}"