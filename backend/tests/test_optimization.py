"""Tests for optimization agent."""
import pytest

from app.agents.optimization.solver import (
    OptimizationSolver,
    OptimizationInput,
)


class TestOptimizationSolver:
    """Test the MILP optimization solver produces valid dispatch plans."""

    def test_produces_dispatch_plan_for_all_intervals(self):
        """Given valid inputs, solver produces dispatch_plan for all 48 intervals."""
        solver = OptimizationSolver()
        optimizer_input = OptimizationInput(
            optimization_strategy={
                "strategy": "peak_shave",
                "shave_kw": 80.0,
                "reserve_soc_pct": 0.30,
                "target_soc_end": 0.50,
            },
            load_forecast=[500.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.70,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
        )

        result = solver.solve(optimizer_input)

        assert result.dispatch_plan is not None
        assert len(result.dispatch_plan) == 48
        assert result.current_dispatch_index == 0
        assert result.dispatch_action is not None
        assert result.dispatch_action.action in ("discharge", "charge", "hold")

    def test_soc_never_below_20_percent(self):
        """SOC should never go below 20% in any interval."""
        solver = OptimizationSolver()
        optimizer_input = OptimizationInput(
            optimization_strategy={
                "strategy": "peak_shave",
                "shave_kw": 100.0,
                "reserve_soc_pct": 0.20,
                "target_soc_end": 0.20,
            },
            load_forecast=[900.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.25,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
        )

        result = solver.solve(optimizer_input)

        for interval in result.dispatch_plan:
            if interval.target_soc is not None:
                assert interval.target_soc >= 0.20

    def test_discharge_never_exceeds_100kw(self):
        """Discharge should never exceed 100kW per 30-min interval."""
        solver = OptimizationSolver()
        optimizer_input = OptimizationInput(
            optimization_strategy={
                "strategy": "peak_shave",
                "shave_kw": 150.0,
                "reserve_soc_pct": 0.20,
                "target_soc_end": 0.50,
            },
            load_forecast=[900.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.90,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
        )

        result = solver.solve(optimizer_input)

        for interval in result.dispatch_plan:
            if interval.discharge_kw is not None:
                assert interval.discharge_kw <= 100.0

    def test_fallback_to_hold_when_soc_too_low(self):
        """When battery_soc < 0.20, should force 'hold' action."""
        solver = OptimizationSolver()
        optimizer_input = OptimizationInput(
            optimization_strategy={
                "strategy": "peak_shave",
                "shave_kw": 80.0,
                "reserve_soc_pct": 0.20,
                "target_soc_end": 0.50,
            },
            load_forecast=[500.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.15,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
        )

        result = solver.solve(optimizer_input)

        assert result.dispatch_action.action == "hold"

    def test_fallback_to_conservative_when_strategy_missing(self):
        """When optimization_strategy is missing, use conservative fallback."""
        solver = OptimizationSolver()
        optimizer_input = OptimizationInput(
            optimization_strategy={},
            load_forecast=[500.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.50,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
        )

        result = solver.solve(optimizer_input)

        assert result.dispatch_action is not None

    def test_warm_start_from_previous_plan(self):
        """When previous_dispatch_plan provided, use as warm start."""
        solver = OptimizationSolver()

        previous_plan = [
            {
                "interval": i,
                "action": "discharge",
                "discharge_kw": 50.0,
                "charge_kw": None,
                "target_soc": 0.60 - (i * 0.005),
                "expected_savings_rm": 5.0,
            }
            for i in range(48)
        ]

        optimizer_input = OptimizationInput(
            optimization_strategy={
                "strategy": "peak_shave",
                "shave_kw": 80.0,
                "reserve_soc_pct": 0.30,
                "target_soc_end": 0.50,
            },
            load_forecast=[500.0] * 48,
            tariff_window="PEAK",
            battery_soc=0.60,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=5,
            previous_dispatch_plan=previous_plan,
        )

        result = solver.solve(optimizer_input)

        assert result.dispatch_plan is not None
        assert result.current_dispatch_index == 5
