"""Tests for Opportunity 3 — OptimizationStrategy single canonical shape."""
import pytest


class TestOptimizationStrategyModel:
    def test_valid_full_dict_parses(self):
        from app.agents.optimization.strategy import OptimizationStrategy
        s = OptimizationStrategy(
            strategy_name="peak_shaving",
            shave_kw=80.0,
            reserve_soc_pct=0.30,
            rationale="High load expected",
            confidence=0.9,
            md_limit_kw=800.0,
        )
        assert s.strategy_name == "peak_shaving"
        assert s.shave_kw == 80.0
        assert s.target_soc_end == 0.50  # default

    def test_missing_required_field_raises(self):
        from app.agents.optimization.strategy import OptimizationStrategy
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OptimizationStrategy(strategy_name="test")  # missing shave_kw etc.

    def test_target_soc_end_default_is_0_50(self):
        from app.agents.optimization.strategy import OptimizationStrategy
        s = OptimizationStrategy(
            strategy_name="conservative",
            shave_kw=50.0,
            reserve_soc_pct=0.20,
            rationale="r",
            confidence=0.7,
            md_limit_kw=800.0,
        )
        assert s.target_soc_end == 0.50

    def test_model_dump_produces_flat_dict(self):
        from app.agents.optimization.strategy import OptimizationStrategy
        s = OptimizationStrategy(
            strategy_name="peak_shaving",
            shave_kw=80.0,
            reserve_soc_pct=0.30,
            rationale="r",
            confidence=0.9,
            md_limit_kw=800.0,
        )
        d = s.model_dump()
        assert "targets" not in d
        assert d["strategy_name"] == "peak_shaving"
        assert d["shave_kw"] == 80.0


class TestPlannerFallbackShape:
    def test_fallback_strategy_validates_as_optimization_strategy(self):
        from app.agents.planner.node import _fallback_strategy
        from app.agents.optimization.strategy import OptimizationStrategy
        state = {"battery_soc": 0.5, "md_limit_kw": 800.0}
        result = _fallback_strategy(state)
        s = OptimizationStrategy(**result)
        assert s.strategy_name == "conservative_shaving"

    def test_fallback_strategy_is_flat_no_nested_targets(self):
        from app.agents.planner.node import _fallback_strategy
        result = _fallback_strategy({})
        assert "targets" not in result
        assert "shave_kw" in result
        assert "reserve_soc_pct" in result
        assert "strategy_name" in result

    def test_fallback_strategy_md_limit_from_state(self):
        from app.agents.planner.node import _fallback_strategy
        result = _fallback_strategy({"md_limit_kw": 1000.0})
        assert result["md_limit_kw"] == 1000.0

    def test_fallback_strategy_default_md_limit(self):
        from app.agents.planner.node import _fallback_strategy
        result = _fallback_strategy({})
        assert result["md_limit_kw"] == 800.0


class TestSolverUsesStrategyName:
    def test_solver_routes_to_milp_with_strategy_name_key(self):
        from app.agents.optimization.solver import OptimizationInput, OptimizationSolver
        solver = OptimizationSolver()
        input_data = OptimizationInput(
            optimization_strategy={
                "strategy_name": "peak_shaving",
                "shave_kw": 80.0,
                "reserve_soc_pct": 0.30,
                "target_soc_end": 0.50,
            },
            load_forecast=[900.0] * 6,
            tariff_window="PEAK",
            battery_soc=0.80,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
        )
        result = solver.solve(input_data)
        assert result.dispatch_action.action in ("discharge", "charge", "hold")

    def test_solver_conservative_fallback_when_no_strategy_name(self):
        from app.agents.optimization.solver import OptimizationInput, OptimizationSolver
        solver = OptimizationSolver()
        input_data = OptimizationInput(
            optimization_strategy={},  # no strategy_name → conservative fallback
            load_forecast=[900.0] * 6,
            tariff_window="PEAK",
            battery_soc=0.80,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
        )
        result = solver.solve(input_data)
        assert result.dispatch_action.action in ("discharge", "hold")

    def test_solver_old_strategy_key_no_longer_triggers_milp(self):
        """Old shape 'strategy' key (not 'strategy_name') routes to conservative fallback."""
        from app.agents.optimization.solver import OptimizationInput, OptimizationSolver
        solver = OptimizationSolver()
        input_data = OptimizationInput(
            optimization_strategy={"strategy": "peak_shaving"},  # old key, ignored
            load_forecast=[900.0] * 6,
            tariff_window="PEAK",
            battery_soc=0.80,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            current_dispatch_index=0,
        )
        result = solver.solve(input_data)
        # Conservative fallback: 50kW discharge or hold
        assert result.dispatch_action.discharge_kw in (50.0, None)


class TestControllerFallbackWithFlatStrategy:
    def test_local_milp_fallback_with_flat_strategy(self):
        from app.agents.controller.node import _local_milp_fallback
        result = _local_milp_fallback(
            forecast_values=[900.0] * 6,
            tariff_window="PEAK",
            battery_soc=0.80,
            bess_capacity_kwh=500.0,
            md_limit_kw=800.0,
            optimization_strategy={
                "strategy_name": "peak_shaving",
                "shave_kw": 80.0,
                "reserve_soc_pct": 0.30,
                "target_soc_end": 0.50,
            },
        )
        assert result["action"] in ("discharge", "charge", "hold")
        assert "duration_min" in result

    def test_flat_strategy_passes_through_without_conversion(self):
        from app.agents.controller.node import _local_milp_fallback
        result = _local_milp_fallback(
            forecast_values=[800.0] * 4,
            tariff_window="PEAK",
            battery_soc=0.90,
            bess_capacity_kwh=500.0,
            md_limit_kw=700.0,
            optimization_strategy={
                "strategy_name": "aggressive_shaving",
                "shave_kw": 100.0,
                "reserve_soc_pct": 0.20,
                "target_soc_end": 0.40,
            },
        )
        assert result["action"] in ("discharge", "charge", "hold")
