"""Tests for OptimizationSolver energy rate consistency."""
import pytest
from app.agents.optimization.solver import OptimizationInput, OptimizationSolver
from app.agents.auditor.evaluation import evaluate_delta


DURATION_MIN = 30


class TestWeekendRateConsistency:
    """Solver and auditor must use same WEEKEND energy rate."""

    def test_weekend_rate_is_0_30_in_solver(self):
        """Solver _get_energy_rate('WEEKEND') must return 0.30, not 0.25."""
        solver = OptimizationSolver()
        rate = solver._get_energy_rate("WEEKEND")
        assert rate == 0.30, f"WEEKEND rate {rate} != 0.30 (auditor uses 0.30)"

    def test_weekend_savings_consistent_between_solver_and_auditor(self):
        """Solver _estimate_savings must match auditor interval_savings_rm for same shave."""
        shave_kw = 80.0
        expected = shave_kw * (DURATION_MIN / 60) * 0.30  # 0.30 RM/kWh

        auditor_result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": shave_kw, "duration_min": DURATION_MIN},
            baseline_load=900.0,
            actual_load=900.0 - shave_kw,
            forecast_kw=900.0,
            tariff_window="WEEKEND",
        )
        assert auditor_result["interval_savings_rm"] == pytest.approx(expected)

        solver = OptimizationSolver()
        input_data = OptimizationInput(
            optimization_strategy={"strategy": "conservative_shaving", "shave_kw": shave_kw, "reserve_soc_pct": 0.30, "target_soc_end": 0.50},
            load_forecast=[900.0] * 6,
            tariff_window="WEEKEND",
            battery_soc=0.80,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
        )
        solver_savings = solver._estimate_savings(shave_kw, input_data)
        assert solver_savings == pytest.approx(auditor_result["interval_savings_rm"], rel=0.01), (
            f"Solver savings {solver_savings} != auditor {auditor_result['interval_savings_rm']} — rate mismatch"
        )

    def test_peak_and_off_peak_rates_unchanged(self):
        """PEAK=0.45, OFF_PEAK=0.22 must be untouched."""
        solver = OptimizationSolver()
        assert solver._get_energy_rate("PEAK") == 0.45
        assert solver._get_energy_rate("OFF_PEAK") == 0.22
