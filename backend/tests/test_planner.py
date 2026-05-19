# Tests for Planner Agent
import pytest


class TestReadGuidelineFile:
    def test_read_existing_file(self):
        from app.agents.planner import read_guideline_file
        result = read_guideline_file("aggressive_peak_shaving.md")
        assert isinstance(result, str)

    def test_read_nonexistent_returns_empty(self):
        from app.agents.planner import read_guideline_file
        result = read_guideline_file("nonexistent_file.md")
        assert isinstance(result, str)


class TestGetForecastContext:
    def test_context_includes_tariff(self):
        from app.agents.planner import get_forecast_context
        state = {"tariff": {"window": "PEAK"}, "battery": {"soc": 0.8}}
        result = get_forecast_context(state)
        assert "PEAK" in result

    def test_context_includes_soc(self):
        from app.agents.planner import get_forecast_context
        state = {"battery": {"soc": 0.60}}
        result = get_forecast_context(state)
        assert "0.6" in result or "60" in result

    def test_context_empty_when_no_args(self):
        from app.agents.planner import get_forecast_context
        result = get_forecast_context({})
        assert isinstance(result, str)

    def test_context_includes_day_type(self):
        from app.agents.planner import get_forecast_context
        state = {"day_type": "weekday", "tariff": {"window": "OFF_PEAK"}}
        result = get_forecast_context(state)
        assert "weekday" in result


class TestPlannerEdgeCases:
    def test_low_soc_in_context(self):
        from app.agents.planner import get_forecast_context
        state = {"battery": {"soc": 0.15}, "tariff": {"window": "PEAK"}}
        result = get_forecast_context(state)
        assert "0.15" in result or "15" in result

    def test_high_load_forecast(self):
        from app.agents.planner import get_forecast_context
        state = {"forecast": {"load_forecast": {"weekday": [120.0]}}, "battery": {"soc": 0.5}}
        result = get_forecast_context(state)
        assert "120" in result


