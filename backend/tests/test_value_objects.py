"""TDD tests for Opportunity 1 — value objects replacing flat AgentState fields."""

import pytest
from app.agents.state import (
    AgentState,
    BatteryState,
    ForecastResult,
    TariffContext,
    DispatchAction,
    DispatchResult,
    OptimizationStrategy,
)


# ---------------------------------------------------------------------------
# Value object contracts
# ---------------------------------------------------------------------------

class TestBatteryState:
    def test_all_fields_accessible(self):
        b = BatteryState(soc=0.8, capacity_kwh=500.0, cycle_count=120.0, temperature_c=31.5)
        assert b["soc"] == 0.8
        assert b["capacity_kwh"] == 500.0
        assert b["cycle_count"] == 120.0
        assert b["temperature_c"] == 31.5

    def test_partial_construction(self):
        b = BatteryState(soc=0.5)
        assert b["soc"] == 0.5
        assert "capacity_kwh" not in b

    def test_soc_fraction_range(self):
        b = BatteryState(soc=0.95, capacity_kwh=200.0)
        assert 0 <= b["soc"] <= 1.0


class TestForecastResult:
    def test_all_fields_accessible(self):
        f = ForecastResult(
            load_forecast={"weekday": [100.0, 110.0, 120.0]},
            confidence={"weekday": 0.85},
            horizon=6,
        )
        assert "weekday" in f["load_forecast"]
        assert f["confidence"]["weekday"] == 0.85
        assert f["horizon"] == 6

    def test_multi_facility(self):
        f = ForecastResult(
            load_forecast={"a": [1.0], "b": [2.0]},
            confidence={"a": 0.9, "b": 0.7},
            horizon=1,
        )
        assert len(f["load_forecast"]) == 2


class TestTariffContext:
    def test_all_fields_accessible(self):
        t = TariffContext(window="PEAK", energy_rate=0.45, demand_charge=97.06, tariff_type="C2")
        assert t["window"] == "PEAK"
        assert t["energy_rate"] == 0.45
        assert t["demand_charge"] == 97.06
        assert t["tariff_type"] == "C2"

    def test_off_peak_zero_demand(self):
        t = TariffContext(window="OFF_PEAK", energy_rate=0.22, demand_charge=0.0, tariff_type="C2")
        assert t["demand_charge"] == 0.0

    def test_weekend_window(self):
        t = TariffContext(window="WEEKEND", energy_rate=0.30, demand_charge=0.0, tariff_type="C2")
        assert t["window"] == "WEEKEND"


class TestDispatchAction:
    def test_discharge_fields(self):
        a = DispatchAction(action="discharge", discharge_kw=80.0, charge_kw=None, duration_min=30, expected_soc_after=0.6)
        assert a["action"] == "discharge"
        assert a["discharge_kw"] == 80.0
        assert a["duration_min"] == 30

    def test_hold_action(self):
        a = DispatchAction(action="hold", duration_min=30)
        assert a["action"] == "hold"

    def test_charge_action(self):
        a = DispatchAction(action="charge", charge_kw=50.0, duration_min=30)
        assert a["action"] == "charge"
        assert a["charge_kw"] == 50.0


class TestDispatchResult:
    def test_all_fields(self):
        r = DispatchResult(
            new_soc=0.75,
            temp_increase_c=0.5,
            cycle_count_delta=0.08,
            action_taken="discharge",
            actual_discharge_kw=80.0,
            efficiency_loss_pct=0.05,
        )
        assert r["new_soc"] == 0.75
        assert r["action_taken"] == "discharge"
        assert r["actual_discharge_kw"] == 80.0

    def test_hold_result(self):
        r = DispatchResult(new_soc=0.8, temp_increase_c=0.1, cycle_count_delta=0.0, action_taken="hold")
        assert r["cycle_count_delta"] == 0.0


class TestOptimizationStrategy:
    def test_required_fields(self):
        s = OptimizationStrategy(
            strategy_name="aggressive_shaving",
            shave_kw=100.0,
            reserve_soc_pct=0.25,
            rationale="Peak period, high forecast",
            confidence=0.85,
        )
        assert s["strategy_name"] == "aggressive_shaving"
        assert s["shave_kw"] == 100.0
        assert s["reserve_soc_pct"] == 0.25

    def test_optional_md_limit(self):
        s = OptimizationStrategy(strategy_name="conservative", shave_kw=50.0, md_limit_kw=800.0)
        assert s["md_limit_kw"] == 800.0


# ---------------------------------------------------------------------------
# AgentState composition — value objects replace flat fields
# ---------------------------------------------------------------------------

class TestAgentStateComposition:
    def test_battery_nested(self):
        state = AgentState(battery=BatteryState(soc=0.8, capacity_kwh=500.0, cycle_count=0.0, temperature_c=30.0))
        assert state["battery"]["soc"] == 0.8
        assert state["battery"]["capacity_kwh"] == 500.0

    def test_forecast_nested(self):
        state = AgentState(
            forecast=ForecastResult(
                load_forecast={"weekday": [800.0, 850.0]},
                confidence={"weekday": 0.9},
                horizon=6,
            )
        )
        assert state["forecast"]["load_forecast"]["weekday"][0] == 800.0

    def test_tariff_nested(self):
        state = AgentState(tariff=TariffContext(window="PEAK", energy_rate=0.45, demand_charge=97.06, tariff_type="C2"))
        assert state["tariff"]["window"] == "PEAK"

    def test_dispatch_action_nested(self):
        state = AgentState(dispatch_action=DispatchAction(action="discharge", discharge_kw=80.0, duration_min=30))
        assert state["dispatch_action"]["action"] == "discharge"

    def test_dispatch_result_nested(self):
        state = AgentState(dispatch_result=DispatchResult(new_soc=0.7, action_taken="discharge"))
        assert state["dispatch_result"]["new_soc"] == 0.7

    def test_optimization_strategy_nested(self):
        state = AgentState(optimization_strategy=OptimizationStrategy(strategy_name="peak_shaving", shave_kw=80.0))
        assert state["optimization_strategy"]["strategy_name"] == "peak_shaving"

    def test_grouped_flat_fields_removed(self):
        """Flat battery/tariff/forecast fields must not appear on AgentState."""
        annotations = AgentState.__annotations__
        assert "battery_soc" not in annotations
        assert "bess_capacity_kwh" not in annotations
        assert "cycle_count" not in annotations
        assert "temperature_c" not in annotations
        assert "tariff_window" not in annotations
        assert "energy_rate" not in annotations
        assert "demand_charge" not in annotations
        assert "load_forecast" not in annotations
        assert "forecast_confidence" not in annotations

    def test_simulation_context_stays_flat(self):
        annotations = AgentState.__annotations__
        assert "day_type" in annotations
        assert "current_time" in annotations
        assert "md_limit_kw" in annotations
        assert "loaded_data" in annotations
        assert "messages" in annotations
        assert "is_end_of_day" in annotations


# ---------------------------------------------------------------------------
# Node contracts: each node writes correct value object keys
# ---------------------------------------------------------------------------

class TestForecastNodeContract:
    def test_returns_forecast_key_not_flat(self):
        import pandas as pd
        from datetime import datetime
        state = AgentState(
            loaded_data={"weekday": {"data": pd.DataFrame({
                "datetime": [datetime(2024, 1, 1 + i // 48, (i * 30) // 60 % 24, (i * 30) % 60) for i in range(60)],
                "kw_import": [float(500 + i * 10) for i in range(60)],
            }).to_dict(orient="records")}},
            current_record_index=55,
            forecast_window=3,
        )
        from app.agents.forecast import forecast_node
        result = forecast_node(state)

        assert "forecast" in result
        assert "load_forecast" not in result
        assert "forecast_confidence" not in result

    def test_forecast_result_has_required_fields(self):
        import pandas as pd
        from datetime import datetime
        state = AgentState(
            loaded_data={"weekday": {"data": pd.DataFrame({
                "datetime": [datetime(2024, 1, 1 + i // 48, (i * 30) // 60 % 24, (i * 30) % 60) for i in range(60)],
                "kw_import": [float(500 + i * 10) for i in range(60)],
            }).to_dict(orient="records")}},
            current_record_index=55,
            forecast_window=3,
        )
        from app.agents.forecast import forecast_node
        result = forecast_node(state)

        f = result["forecast"]
        assert "load_forecast" in f
        assert "confidence" in f
        assert "horizon" in f


class TestTariffNodeContract:
    def test_returns_tariff_key_not_flat(self):
        from datetime import datetime
        from app.agents.tariff.node import TariffNode
        node = TariffNode()
        state = AgentState(current_time=datetime(2024, 6, 3, 15, 0))
        result = node.invoke(state)

        assert "tariff" in result
        assert "tariff_window" not in result
        assert "energy_rate" not in result
        assert "demand_charge" not in result
        assert "tariff_type" not in result

    def test_tariff_context_fields_present(self):
        from datetime import datetime
        from app.agents.tariff.node import TariffNode
        node = TariffNode()
        state = AgentState(current_time=datetime(2024, 6, 3, 15, 0))
        result = node.invoke(state)

        t = result["tariff"]
        assert t["window"] in ("PEAK", "OFF_PEAK", "WEEKEND")
        assert "energy_rate" in t
        assert "demand_charge" in t
        assert "tariff_type" in t


class TestControllerNodeContract:
    def _make_state(self):
        return AgentState(
            battery=BatteryState(soc=0.8, capacity_kwh=500.0, cycle_count=0.0, temperature_c=30.0),
            tariff=TariffContext(window="PEAK", energy_rate=0.45, demand_charge=97.06, tariff_type="C2"),
            forecast=ForecastResult(
                load_forecast={"weekday": [850.0, 830.0]},
                confidence={"weekday": 0.85},
                horizon=6,
            ),
            optimization_strategy=OptimizationStrategy(
                strategy_name="conservative_shaving",
                shave_kw=50.0,
                reserve_soc_pct=0.30,
            ),
            current_facility="weekday",
            md_limit_kw=800.0,
        )

    def test_returns_battery_not_flat_soc(self):
        from unittest.mock import patch
        state = self._make_state()
        with patch("app.agents.controller.node._get_controller_agent") as m:
            m.return_value.invoke.side_effect = Exception("unavailable")
            from app.agents.controller.node import controller_node
            result = controller_node(state)

        assert "battery" in result
        assert "battery_soc" not in result
        assert "bess_capacity_kwh" not in result
        assert "cycle_count" not in result
        assert "temperature_c" not in result

    def test_battery_shape(self):
        from unittest.mock import patch
        state = self._make_state()
        with patch("app.agents.controller.node._get_controller_agent") as m:
            m.return_value.invoke.side_effect = Exception("unavailable")
            from app.agents.controller.node import controller_node
            result = controller_node(state)

        battery = result["battery"]
        assert "soc" in battery
        assert "capacity_kwh" in battery
        assert "cycle_count" in battery
        assert "temperature_c" in battery
        assert 0 <= battery["soc"] <= 1.0

    def test_returns_dispatch_action_and_result(self):
        from unittest.mock import patch
        state = self._make_state()
        with patch("app.agents.controller.node._get_controller_agent") as m:
            m.return_value.invoke.side_effect = Exception("unavailable")
            from app.agents.controller.node import controller_node
            result = controller_node(state)

        assert "dispatch_action" in result
        assert "dispatch_result" in result
        assert result["dispatch_action"]["action"] in ("discharge", "charge", "hold")

    def test_convenience_scalars_present(self):
        from unittest.mock import patch
        state = self._make_state()
        with patch("app.agents.controller.node._get_controller_agent") as m:
            m.return_value.invoke.side_effect = Exception("unavailable")
            from app.agents.controller.node import controller_node
            result = controller_node(state)

        assert "forecast_kw" in result
        assert "actual_load" in result
        assert "last_dispatch_kw" in result
        assert "baseline_load" in result
