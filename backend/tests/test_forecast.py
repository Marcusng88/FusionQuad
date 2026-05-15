import pytest
import torch
from pathlib import Path
from app.data.csv_loader import CSVLoader
from app.ml.forecast_model import ForecastModel, ForecastConfig


@pytest.fixture
def data_dir():
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def loader():
    return CSVLoader()


@pytest.fixture
def sol_data(loader, data_dir):
    """Load SoL (solar) dataset for training."""
    file_path = data_dir / "1. Load Profile (With Solar Installed) SoL.csv"
    return loader.load(file_path)


@pytest.fixture
def e_data(loader, data_dir):
    """Load E (weekday no solar) dataset."""
    file_path = data_dir / "2. Load Profile (No Solar) E.csv"
    return loader.load(file_path)


@pytest.fixture
def sun_data(loader, data_dir):
    """Load SuN (holiday) dataset."""
    file_path = data_dir / "3. Load Profile (No Solar) SuN.csv"
    return loader.load(file_path)


@pytest.fixture
def mi2_data(loader, data_dir):
    """Load Mi2 (solar) dataset."""
    file_path = data_dir / "4. Load Profile (With Solar) Mi2.csv"
    return loader.load(file_path)


class TestForecastModelInit:
    """Tracer bullet: verify model can be initialized."""

    def test_model_creates_with_default_config(self):
        """Model instantiates with default config."""
        model = ForecastModel()
        assert model is not None
        assert isinstance(model, ForecastModel)

    def test_model_has_expected_modules(self):
        """Model has prediction capability via forward pass."""
        model = ForecastModel()
        # Model should produce output of correct shape
        dummy_input = torch.zeros(1, 48, 1)
        output = model.model(dummy_input)
        assert output.shape == (1, 1)
        # Model should be on CPU by default
        assert next(model.model.parameters()).device.type == 'cpu'


class TestForecastModelTraining:
    """Test model training on historical data."""

    def test_model_train_single_file(self, sol_data, tmp_path):
        """Train model on SoL data and verify it runs."""
        model = ForecastModel()
        X, y = model.prepare_sequence(sol_data)

        # Train for 2 epochs
        model.train_model(X, y, epochs=2, verbose=False)

        # Model should be in training mode
        assert model.model.training

    def test_model_train_multiple_files(self, sol_data, e_data, mi2_data, tmp_path):
        """Combine data from multiple files for training."""
        model = ForecastModel()

        # Prepare sequences from each file
        X1, y1 = model.prepare_sequence(sol_data)
        X2, y2 = model.prepare_sequence(e_data)
        X3, y3 = model.prepare_sequence(mi2_data)

        # Concatenate
        X_combined = torch.cat([X1, X2, X3], dim=0)
        y_combined = torch.cat([y1, y2, y3], dim=0)

        # Train
        model.train_model(X_combined, y_combined, epochs=2, verbose=False)

    def test_model_predict_single_step(self, sol_data):
        """Model predicts one step ahead."""
        model = ForecastModel()
        X, y = model.prepare_sequence(sol_data)

        # Train briefly
        model.train_model(X, y, epochs=1, verbose=False)

        # Predict first sample
        X_sample = X[0:1]  # shape: (1, seq_len, input_size)
        pred = model.predict(X_sample)

        assert pred.shape.numel() == 1  # single value
        assert not torch.isnan(pred).any()


class TestForecastAccuracy:
    """Test forecast accuracy on held-out validation data."""

    def test_mape_within_threshold_on_weekday(self, e_data, tmp_path):
        """E (weekday) data should achieve MAPE ≤15%."""
        model = ForecastModel()
        X, y = model.prepare_sequence(e_data)

        # Split: 80% train, 20% validation
        # Use most recent data for validation (last 20%)
        n = len(X)
        split = int(0.8 * n)
        X_train, y_train = X[:split], y[:split]
        X_val, y_val = X[split:], y[split:]

        # Train
        model.train_model(X_train, y_train, epochs=10, verbose=False)

        # Evaluate
        mape = model.evaluate_mape(X_val, y_val)
        assert mape <= 15.0, f"MAPE {mape:.2f}% exceeds 15% threshold"

    def test_mape_on_mi2_weekend(self, mi2_data):
        """Mi2 (weekend with solar) should achieve MAPE ≤20%."""
        model = ForecastModel()
        X, y = model.prepare_sequence(mi2_data)

        split = int(0.8 * len(X))
        X_train, y_train = X[:split], y[:split]
        X_val, y_val = X[split:], y[split:]

        model.train_model(X_train, y_train, epochs=10, verbose=False)

        mape = model.evaluate_mape(X_val, y_val)
        # Weekend with solar has more variance, allow 20%
        assert mape <= 20.0, f"MAPE {mape:.2f}% exceeds 20% for weekend data"

    def test_mape_on_sol_with_solar(self, sol_data):
        """SoL (with solar) should achieve MAPE ≤15%."""
        model = ForecastModel()
        X, y = model.prepare_sequence(sol_data)

        split = int(0.8 * len(X))
        X_train, y_train = X[:split], y[:split]
        X_val, y_val = X[split:], y[split:]

        model.train_model(X_train, y_train, epochs=10, verbose=False)

        mape = model.evaluate_mape(X_val, y_val)
        assert mape <= 15.0, f"MAPE {mape:.2f}% exceeds 15% threshold"


class TestForecastModelPersistence:
    """Test model save/load."""

    def test_save_and_load_weights(self, sol_data, tmp_path):
        """Model weights can be saved and loaded."""
        model = ForecastModel()
        X, y = model.prepare_sequence(sol_data)
        model.train_model(X, y, epochs=1, verbose=False)

        # Save
        save_path = tmp_path / "forecast_weights.pt"
        model.save(save_path)

        # Load into new model
        model2 = ForecastModel()
        model2.load(save_path)

        # Predictions should be identical
        X_sample = X[0:1]
        pred1 = model.predict(X_sample)
        pred2 = model2.predict(X_sample)

        assert torch.allclose(pred1, pred2, atol=1e-6)


class TestForecastSequenceCreation:
    """Test sequence preparation from DataFrame."""

    def test_sequence_length_is_correct(self, e_data):
        """Default sequence length is 48 (24 hours of 30-min intervals)."""
        model = ForecastModel()
        X, y = model.prepare_sequence(e_data)

        assert X.shape[1] == 48  # seq_len

    def test_sequence_handles_missing_kw_import(self, loader, data_dir):
        """DataFrame without kw_import column raises informative error."""
        import pandas as pd
        df = pd.DataFrame({'datetime': pd.date_range('2025-01-01', periods=100, freq='30min')})

        model = ForecastModel()
        with pytest.raises(KeyError):
            model.prepare_sequence(df)

    def test_minimum_data_length(self):
        """Model requires at least sequence_length + 1 rows."""
        import pandas as pd
        model = ForecastModel()

        # Too short
        df = pd.DataFrame({
            'datetime': pd.date_range('2025-01-01', periods=10, freq='30min'),
            'kw_import': range(10)
        })

        with pytest.raises(ValueError):
            model.prepare_sequence(df)

        # Just enough
        df = pd.DataFrame({
            'datetime': pd.date_range('2025-01-01', periods=49, freq='30min'),
            'kw_import': range(49)
        })
        X, y = model.prepare_sequence(df)
        assert X.shape[0] == 1