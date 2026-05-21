"""Tests for OptimizationStrategy shape — planner output and solver routing."""
import pytest


class TestPlannerFallbackShape:
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

    def test_fallback_strategy_has_required_keys(self):
        from app.agents.planner.node import _fallback_strategy
        result = _fallback_strategy({})
        assert result["strategy_name"] == "conservative_shaving"
        assert result["target_soc_end"] == 0.50


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
        assert result.dispatch_action.discharge_kw in (50.0, None)
