from datetime import datetime
import pytest
from app.agents.tariff.node import (
    TariffNode,
    DEMAND_RATES,
    _get_tariff_window,
    _is_holiday,
)
from app.agents.tariff.rates import TARIFF_RATES
from app.schemas.agent import AgentState


class TestGetTariffWindow:
    def test_weekend_saturday_returns_weekend(self):
        saturday = datetime(2025, 5, 17, 10, 0)
        assert _get_tariff_window(saturday) == "WEEKEND"

    def test_weekend_sunday_returns_weekend(self):
        sunday = datetime(2025, 5, 18, 14, 0)
        assert _get_tariff_window(sunday) == "WEEKEND"

    def test_peak_hours_weekday(self):
        wednesday_2pm = datetime(2025, 5, 14, 14, 0)
        assert _get_tariff_window(wednesday_2pm) == "PEAK"
        wednesday_2159 = datetime(2025, 5, 14, 21, 59)
        assert _get_tariff_window(wednesday_2159) == "PEAK"

    def test_peak_boundary_at_22(self):
        wednesday_10pm = datetime(2025, 5, 14, 22, 0)
        assert _get_tariff_window(wednesday_10pm) == "OFF_PEAK"

    def test_peak_boundary_at_14(self):
        wednesday_2pm = datetime(2025, 5, 14, 14, 0)
        assert _get_tariff_window(wednesday_2pm) == "PEAK"

    def test_off_peak_morning_weekday(self):
        wednesday_7am = datetime(2025, 5, 14, 7, 0)
        assert _get_tariff_window(wednesday_7am) == "OFF_PEAK"

    def test_off_peak_night_weekday(self):
        wednesday_2330 = datetime(2025, 5, 14, 23, 30)
        assert _get_tariff_window(wednesday_2330) == "OFF_PEAK"

    def test_weekend_takes_precedence_over_peak_hours(self):
        saturday_3pm = datetime(2025, 5, 17, 15, 0)
        assert _get_tariff_window(saturday_3pm) == "WEEKEND"


class TestIsHoliday:
    def test_holiday_detected(self):
        new_year = datetime(2025, 1, 1, 0, 0)
        assert _is_holiday(new_year) is True

    def test_non_holiday(self):
        wednesday = datetime(2025, 5, 14, 10, 0)
        assert _is_holiday(wednesday) is False


class TestTariffRates:
    def test_c2_peak_energy_rate(self):
        assert TARIFF_RATES["C2"].peak == pytest.approx(0.45)

    def test_c2_off_peak_energy_rate(self):
        assert TARIFF_RATES["C2"].off_peak == pytest.approx(0.22)

    def test_c2_weekend_energy_rate(self):
        assert TARIFF_RATES["C2"].weekend == pytest.approx(0.30)

    def test_c2_demand_rate(self):
        assert DEMAND_RATES["C2"] == pytest.approx(97.06)

    def test_c1_lower_demand_than_c2(self):
        assert TARIFF_RATES["C1"].demand < TARIFF_RATES["C2"].demand


class TestTariffNode:
    def test_peak_window_sets_correct_rates(self):
        node = TariffNode()
        state = AgentState(
            current_time=datetime(2025, 5, 14, 15, 0),
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_window"] == "PEAK"
        assert result["energy_rate"] == pytest.approx(0.45)
        assert result["demand_charge"] == pytest.approx(97.06)

    def test_off_peak_window_zero_demand(self):
        node = TariffNode()
        state = AgentState(
            current_time=datetime(2025, 5, 14, 7, 0),
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_window"] == "OFF_PEAK"
        assert result["energy_rate"] == pytest.approx(0.22)
        assert result["demand_charge"] == 0.0

    def test_weekend_window_zero_demand(self):
        node = TariffNode()
        state = AgentState(
            current_time=datetime(2025, 5, 17, 14, 0),
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_window"] == "WEEKEND"
        assert result["energy_rate"] == pytest.approx(0.30)
        assert result["demand_charge"] == 0.0

    def test_e1_tariff_type(self):
        node = TariffNode(tariff_type="E1")
        state = AgentState(
            current_time=datetime(2025, 5, 14, 15, 0),
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_type"] == "E1"
        assert result["energy_rate"] == pytest.approx(0.45)
        assert result["demand_charge"] == pytest.approx(89.27)

    def test_holiday_treated_as_weekend(self):
        node = TariffNode()
        state = AgentState(
            current_time=datetime(2025, 1, 1, 15, 0),
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_window"] == "WEEKEND"

    def test_none_current_time_defaults_to_peak(self):
        node = TariffNode()
        state = AgentState(
            current_time=None,
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            tariff_type=None,
        )
        result = node.invoke(state)
        assert result["tariff_window"] == "PEAK"
        assert result["energy_rate"] == pytest.approx(0.45)
