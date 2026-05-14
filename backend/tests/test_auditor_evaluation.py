"""Tests for Auditor evaluation tools."""

import pytest
from app.agents.auditor.evaluation import (
    evaluate_delta,
    evaluate_rules,
    should_run_llm,
)


class TestEvaluateDelta:
    """Tests for evaluate_delta numeric scoring."""

    def test_shave_calculation_positive(self):
        """Discharge reduces load - should calculate positive shave."""
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": 80, "duration_min": 30},
            baseline_load=920.0,
            actual_load=840.0,
            forecast_kw=850.0,
            tariff_window="PEAK",
        )
        assert result["shave_kw"] == 80.0
        assert result["shave_pct"] > 0

    def test_shave_calculation_no_improvement(self):
        """When actual_load >= baseline_load, no shave credit."""
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": 80, "duration_min": 30},
            baseline_load=800.0,
            actual_load=820.0,
            forecast_kw=850.0,
            tariff_window="PEAK",
        )
        assert result["shave_kw"] == 0.0

    def test_forecast_error_calculation(self):
        """Forecast error should be percentage deviation from forecast."""
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": 80, "duration_min": 30},
            baseline_load=920.0,
            actual_load=850.0,
            forecast_kw=800.0,
            tariff_window="PEAK",
        )
        assert result["forecast_error_pct"] == 6.25

    def test_delta_score_range(self):
        """Delta score should be 0-100."""
        result = evaluate_delta(
            dispatch_result={"action_taken": "discharge"},
            dispatch_action={"action": "discharge", "discharge_kw": 80, "duration_min": 30},
            baseline_load=920.0,
            actual_load=840.0,
            forecast_kw=850.0,
            tariff_window="PEAK",
        )
        assert 0 <= result["delta_score"] <= 100

    def test_none_inputs_returns_zeros(self):
        """None dispatch_result should return zeroed evaluation."""
        result = evaluate_delta(
            dispatch_result=None,
            dispatch_action=None,
            baseline_load=920.0,
            actual_load=840.0,
            forecast_kw=850.0,
            tariff_window="PEAK",
        )
        assert result["shave_kw"] == 0.0
        assert result["delta_score"] == 0.0


class TestEvaluateRules:
    """Tests for evaluate_rules safety checks."""

    def test_passes_within_limits(self):
        """Should pass when all metrics within safe limits."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 0.5, "actual_discharge_kw": 80},
            battery_soc=0.65,
            cycle_count=1500.0,
            tariff_window="PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    def test_critical_soc_low(self):
        """SOC below 20% is critical violation."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 0.5, "actual_discharge_kw": 80},
            battery_soc=0.15,
            cycle_count=1500.0,
            tariff_window="PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is False
        violation = next(v for v in result["violations"] if v["rule"] == "soc_minimum")
        assert violation["severity"] == "critical"

    def test_critical_cycle_count_exceeded(self):
        """Cycle count above 3000 is critical violation."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 0.5, "actual_discharge_kw": 80},
            battery_soc=0.65,
            cycle_count=3500.0,
            tariff_window="PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is False
        violation = next(v for v in result["violations"] if v["rule"] == "cycle_count_max")
        assert violation["severity"] == "critical"

    def test_critical_temperature_exceeded(self):
        """Temperature increase above 5C is critical."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 6.0, "actual_discharge_kw": 80},
            battery_soc=0.65,
            cycle_count=1500.0,
            tariff_window="PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is False
        violation = next(v for v in result["violations"] if v["rule"] == "temperature_rise")
        assert violation["severity"] == "critical"

    def test_critical_power_exceeded(self):
        """Discharge above 100kW exceeds inverter limit."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 0.5, "actual_discharge_kw": 120},
            battery_soc=0.65,
            cycle_count=1500.0,
            tariff_window="PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is False
        violation = next(v for v in result["violations"] if v["rule"] == "inverter_power_limit")
        assert violation["severity"] == "critical"

    def test_warning_off_peak_discharge(self):
        """Discharging during OFF_PEAK is suboptimal (warning)."""
        result = evaluate_rules(
            dispatch_result={"temp_increase_c": 0.5, "actual_discharge_kw": 80},
            battery_soc=0.65,
            cycle_count=1500.0,
            tariff_window="OFF_PEAK",
            dispatch_action={"action": "discharge"},
        )
        assert result["passed"] is True
        violation = next(v for v in result["violations"] if v["rule"] == "off_peak_discharge")
        assert violation["severity"] == "warning"


class TestShouldRunLLM:
    """Tests for LLM evaluation trigger logic."""

    def test_triggers_on_rule_violations(self):
        """Should run LLM when rules are violated."""
        rule_eval = {"passed": False, "violations": [{"rule": "test", "severity": "critical", "detail": "test"}]}
        delta_eval = {"delta_score": 80, "forecast_error_pct": 5.0}
        assert should_run_llm(delta_eval, rule_eval) is True

    def test_triggers_on_low_delta_score(self):
        """Should run LLM when delta_score < 50."""
        rule_eval = {"passed": True, "violations": []}
        delta_eval = {"delta_score": 40, "forecast_error_pct": 5.0}
        assert should_run_llm(delta_eval, rule_eval) is True

    def test_triggers_on_high_forecast_error(self):
        """Should run LLM when forecast_error > 20%."""
        rule_eval = {"passed": True, "violations": []}
        delta_eval = {"delta_score": 70, "forecast_error_pct": 25.0}
        assert should_run_llm(delta_eval, rule_eval) is True

    def test_no_llm_needed_optimal_case(self):
        """Should NOT run LLM when all metrics are good."""
        rule_eval = {"passed": True, "violations": []}
        delta_eval = {"delta_score": 85, "forecast_error_pct": 10.0}
        assert should_run_llm(delta_eval, rule_eval) is False
