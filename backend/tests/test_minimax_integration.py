"""Tests for MiniMax model integration with the multi-agent system.

Unit tests run always. Integration tests (marked `integration`) hit the real
MiniMax API and are skipped when MINIMAX_API_KEY is not set.

Run integration tests:
    pytest tests/test_minimax_integration.py -m integration -v
"""

from __future__ import annotations

import os

import pytest

import app.core.model_selection as model_selection
from app.core.model_selection import resolve_deepagents_model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimax_key_present() -> bool:
    key = os.getenv("MINIMAX_API_KEY", "").strip()
    if key:
        return True
    env_vals = model_selection._load_dotenv()
    return bool(str(env_vals.get("MINIMAX_API_KEY", "")).strip())


def _minimax_runtime_available() -> bool:
    return model_selection._model_runtime_available("minimax:any")


# ---------------------------------------------------------------------------
# Unit tests — no API calls
# ---------------------------------------------------------------------------

class TestMinimaxModelSelection:
    def test_minimax_selected_when_key_and_runtime_present(self, monkeypatch):
        model_selection._load_dotenv.cache_clear()
        monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        monkeypatch.setenv("MINIMAX_MODEL", "minimax:MiniMax-M2.7")
        monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {})
        monkeypatch.setattr(model_selection, "_model_runtime_available", lambda m: True)

        model = resolve_deepagents_model("fallback:model")
        assert model == "minimax:MiniMax-M2.7"

    def test_minimax_skipped_when_runtime_missing(self, monkeypatch):
        model_selection._load_dotenv.cache_clear()
        monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
        monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
        monkeypatch.setenv("MINIMAX_MODEL", "minimax:MiniMax-M2.7")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(model_selection, "_load_dotenv", lambda: {})
        monkeypatch.setattr(model_selection, "_model_runtime_available", lambda m: False)

        model = resolve_deepagents_model("fallback:model")
        assert model == "fallback:model"

    def test_minimax_key_read_from_dotenv(self, monkeypatch):
        model_selection._load_dotenv.cache_clear()
        monkeypatch.delenv("DEEPAGENTS_MODEL", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.setattr(
            model_selection,
            "_load_dotenv",
            lambda: {"MINIMAX_API_KEY": "dotenv-key", "MINIMAX_MODEL": "minimax:MiniMax-M2.7"},
        )
        monkeypatch.setattr(model_selection, "_model_runtime_available", lambda m: True)

        model = resolve_deepagents_model("fallback:model")
        assert model == "minimax:MiniMax-M2.7"

    def test_real_env_resolves_minimax(self):
        """Verify .env is wired correctly — minimax selected if key+runtime present."""
        model_selection._load_dotenv.cache_clear()
        model = resolve_deepagents_model("fallback:model")
        if _minimax_key_present() and _minimax_runtime_available():
            assert model.startswith("minimax:"), f"Expected minimax model, got: {model}"
        else:
            pytest.skip("MINIMAX_API_KEY not set or runtime not installed")


# ---------------------------------------------------------------------------
# Integration tests — real API calls
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMinimaxPlannerIntegration:
    """Invoke planner_node end-to-end with the MiniMax model."""

    @pytest.fixture(autouse=True)
    def require_minimax(self):
        model_selection._load_dotenv.cache_clear()
        if not _minimax_key_present():
            pytest.skip("MINIMAX_API_KEY not set")
        if not _minimax_runtime_available():
            pytest.skip("minimax runtime not installed (pip install langchain-minimax or litellm)")

    def test_planner_node_returns_optimization_strategy(self):
        from app.agents.planner.node import _PLANNER_AGENT, planner_node

        # Reset cached agent so it reinitializes with current env
        import app.agents.planner.node as planner_mod
        planner_mod._PLANNER_AGENT = None

        state = {
            "day_type": "weekday",
            "battery": {"soc": 0.65, "capacity_kwh": 500.0, "cycle_count": 10.0, "temperature_c": 30.0},
            "tariff": {"window": "PEAK", "energy_rate": 0.365, "demand_charge": 97.06, "tariff_type": "C2"},
            "forecast": {"load_forecast": {"weekday": [620.0, 640.0, 630.0]}, "confidence": {"weekday": 0.85}, "horizon": 3},
            "md_limit_kw": 800.0,
            "loaded_data": {},
            "current_facility": "weekday",
        }

        result = planner_node(state)

        assert "optimization_strategy" in result
        strategy = result["optimization_strategy"]
        assert strategy.get("strategy_name"), "strategy_name must be non-empty"
        assert isinstance(strategy.get("shave_kw"), float)
        assert 0.0 <= float(strategy.get("confidence", 0.0)) <= 1.0

    def test_planner_uses_minimax_model(self):
        model = resolve_deepagents_model("fallback:model")
        assert model.startswith("minimax:"), f"Expected minimax model, got: {model}"


@pytest.mark.integration
class TestMinimaxAuditorIntegration:
    """Invoke auditor_node end-to-end with the MiniMax model."""

    @pytest.fixture(autouse=True)
    def require_minimax(self):
        model_selection._load_dotenv.cache_clear()
        if not _minimax_key_present():
            pytest.skip("MINIMAX_API_KEY not set")
        if not _minimax_runtime_available():
            pytest.skip("minimax runtime not installed")

    def test_auditor_node_returns_decision_log(self):
        import app.agents.auditor.agent as auditor_mod
        auditor_mod._AUDITOR_AGENT_TICK = None
        auditor_mod._AUDITOR_AGENT_EOD = None

        from app.agents.auditor.agent import auditor_node

        state = {
            "session_id": "minimax-test-session",
            "day_type": "weekday",
            "current_interval": 1,
            "is_end_of_day": False,
            "battery": {"soc": 0.65, "capacity_kwh": 500.0, "cycle_count": 10.0, "temperature_c": 30.0},
            "tariff": {"window": "PEAK", "energy_rate": 0.365, "demand_charge": 97.06, "tariff_type": "C2"},
            "dispatch_action": {"action": "discharge", "discharge_kw": 80.0, "charge_kw": None, "duration_min": 30},
            "dispatch_result": {"new_soc": 0.58, "temp_increase_c": 0.4, "action_taken": "discharge", "actual_discharge_kw": 80.0, "efficiency_loss_pct": 0.05},
            "baseline_load": 720.0,
            "actual_load": 640.0,
            "forecast_kw": 700.0,
            "md_limit_kw": 800.0,
            "total_savings_rm": 0.0,
            "within_limit_ticks": 0,
            "decision_log": [],
        }

        result = auditor_node(state)

        assert "decision_log" in result
        assert len(result["decision_log"]) == 1
        entry = result["decision_log"][0]
        assert "perceive" in entry
        assert "reason" in entry
        assert "act" in entry
