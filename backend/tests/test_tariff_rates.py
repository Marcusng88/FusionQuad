"""TDD tests for single-source tariff rates (Opportunity 2)."""
import pytest
from app.agents.tariff.rates import TARIFF_RATES, TariffRates, get_energy_rate


class TestTariffRatesSource:
    """Central rates module is the single source of truth."""

    def test_tariff_rates_importable(self):
        """Central rates module must exist and be importable."""
        assert TARIFF_RATES is not None

    def test_c2_has_all_windows(self):
        rates = TARIFF_RATES["C2"]
        assert rates.peak > 0
        assert rates.off_peak > 0
        assert rates.weekend > 0
        assert rates.demand > 0

    def test_c2_peak_rate(self):
        assert TARIFF_RATES["C2"].peak == pytest.approx(0.45)

    def test_c2_off_peak_rate(self):
        assert TARIFF_RATES["C2"].off_peak == pytest.approx(0.22)

    def test_c2_weekend_rate(self):
        assert TARIFF_RATES["C2"].weekend == pytest.approx(0.30)

    def test_c2_demand_charge(self):
        assert TARIFF_RATES["C2"].demand == pytest.approx(97.06)

    def test_c1_lower_demand(self):
        assert TARIFF_RATES["C1"].demand < TARIFF_RATES["C2"].demand

    def test_all_tariff_types_present(self):
        for t in ("C2", "E2", "C1", "E1"):
            assert t in TARIFF_RATES, f"{t} missing from TARIFF_RATES"


class TestGetEnergyRate:
    """get_energy_rate helper returns correct rate for window."""

    def test_peak_window(self):
        assert get_energy_rate("C2", "PEAK") == pytest.approx(0.45)

    def test_off_peak_window(self):
        assert get_energy_rate("C2", "OFF_PEAK") == pytest.approx(0.22)

    def test_weekend_window(self):
        assert get_energy_rate("C2", "WEEKEND") == pytest.approx(0.30)

    def test_unknown_tariff_type_defaults_to_c2(self):
        assert get_energy_rate("UNKNOWN", "PEAK") == pytest.approx(0.45)

    def test_unknown_window_defaults_to_off_peak(self):
        assert get_energy_rate("C2", "UNKNOWN") == pytest.approx(0.22)


class TestRateConsistencyAcrossModules:
    """Solver and auditor must use same rates as central source."""

    def test_solver_uses_central_weekend_rate(self):
        from app.agents.optimization.solver import OptimizationSolver
        solver = OptimizationSolver()
        assert solver._get_energy_rate("WEEKEND") == pytest.approx(TARIFF_RATES["C2"].weekend)

    def test_solver_uses_central_peak_rate(self):
        from app.agents.optimization.solver import OptimizationSolver
        solver = OptimizationSolver()
        assert solver._get_energy_rate("PEAK") == pytest.approx(TARIFF_RATES["C2"].peak)

    def test_solver_uses_central_off_peak_rate(self):
        from app.agents.optimization.solver import OptimizationSolver
        solver = OptimizationSolver()
        assert solver._get_energy_rate("OFF_PEAK") == pytest.approx(TARIFF_RATES["C2"].off_peak)

    def test_evaluation_savings_match_central_weekend_rate(self):
        from app.agents.auditor.evaluation import evaluate_delta
        shave_kw = 80.0
        duration_min = 30
        expected = shave_kw * (duration_min / 60) * TARIFF_RATES["C2"].weekend
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": shave_kw, "duration_min": duration_min},
            baseline_load=900.0,
            actual_load=900.0 - shave_kw,
            forecast_kw=900.0,
            tariff_window="WEEKEND",
        )
        assert result["interval_savings_rm"] == pytest.approx(expected)

    def test_evaluation_savings_match_central_peak_rate(self):
        from app.agents.auditor.evaluation import evaluate_delta
        shave_kw = 80.0
        duration_min = 30
        expected = shave_kw * (duration_min / 60) * TARIFF_RATES["C2"].peak
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": shave_kw, "duration_min": duration_min},
            baseline_load=900.0,
            actual_load=900.0 - shave_kw,
            forecast_kw=900.0,
            tariff_window="PEAK",
        )
        assert result["interval_savings_rm"] == pytest.approx(expected)
