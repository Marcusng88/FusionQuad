"""Singleton BESS service — guardrails, physics simulation, and MILP dispatch."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.agents.config import MAX_SOC, MIN_SOC
from app.agents.optimization.solver import OptimizationInput, OptimizationSolver

_AMBIENT_TEMP_C = 25.0
_COOLING_RATE = 0.05
_CHARGE_EFFICIENCY = 0.95
_DISCHARGE_EFFICIENCY_LOSS = 0.05


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str
    override_action: str | None = None


@dataclass
class ExecutionResult:
    new_soc: float
    net_temp_delta_c: float
    cycle_count_delta: float
    action_taken: str
    actual_discharge_kw: float
    efficiency_loss_pct: float


class BatteryManager:
    _instance: BatteryManager | None = None

    def __init__(self) -> None:
        self._solver = OptimizationSolver()

    @classmethod
    def get(cls) -> BatteryManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_guardrails(
        self,
        action: str,
        power_kw: float,
        soc: float,
        temperature_c: float,
        cycle_count: float,
    ) -> GuardrailResult:
        if soc < MIN_SOC:
            return GuardrailResult(
                allowed=False,
                reason=f"SOC {soc:.1%} below minimum {MIN_SOC:.1%}",
                override_action="hold",
            )
        if temperature_c >= 45.0:
            return GuardrailResult(
                allowed=False,
                reason=f"Temperature {temperature_c:.1f}°C exceeds thermal limit 45°C",
                override_action="hold",
            )
        if cycle_count >= 3000:
            return GuardrailResult(
                allowed=False,
                reason=f"Cycle count {cycle_count:.0f} exceeds limit 3000",
                override_action="hold",
            )
        return GuardrailResult(allowed=True, reason="OK")

    def execute_action(
        self,
        action: str,
        power_kw: float,
        duration_min: int,
        soc: float,
        capacity_kwh: float,
        temperature_c: float,
    ) -> ExecutionResult:
        if action == "discharge":
            energy_kwh = power_kw * (duration_min / 60)
            actual_discharge = energy_kwh * (1 - _DISCHARGE_EFFICIENCY_LOSS)
            new_soc = max(0.0, soc - actual_discharge / capacity_kwh)
            heat_gain = 0.5 * (power_kw / 100)
            cycle_delta = energy_kwh / (2 * capacity_kwh)
            actual_kw = power_kw
        elif action == "charge":
            energy_kwh = power_kw * (duration_min / 60)
            new_soc = min(soc + energy_kwh * _CHARGE_EFFICIENCY / capacity_kwh, MAX_SOC)
            heat_gain = 0.2 * (power_kw / 100)
            cycle_delta = 0.0
            actual_kw = 0.0
        else:
            new_soc = soc
            heat_gain = 0.1
            cycle_delta = 0.0
            actual_kw = 0.0

        cooling = _COOLING_RATE * max(0.0, temperature_c - _AMBIENT_TEMP_C)
        return ExecutionResult(
            new_soc=new_soc,
            net_temp_delta_c=heat_gain - cooling,
            cycle_count_delta=cycle_delta,
            action_taken=action,
            actual_discharge_kw=actual_kw,
            efficiency_loss_pct=_DISCHARGE_EFFICIENCY_LOSS,
        )

    def optimize_dispatch(
        self,
        load_forecast: list[float],
        tariff_window: str,
        strategy_params: dict,
        battery_soc: float,
        bess_capacity_kwh: float,
        md_limit_kw: float,
        max_discharge_kw: float,
    ) -> dict:
        input_data = OptimizationInput(
            optimization_strategy=strategy_params,
            load_forecast=load_forecast,
            tariff_window=tariff_window,
            battery_soc=battery_soc,
            bess_capacity_kwh=bess_capacity_kwh,
            md_limit_kw=md_limit_kw,
            current_dispatch_index=0,
            previous_dispatch_plan=None,
            max_discharge_kw=max_discharge_kw,
        )
        result = self._solver.solve(input_data)
        action = asdict(result.dispatch_action)
        action["expected_soc_after"] = result.dispatch_action.expected_soc_after
        return {"dispatch_action": action}

    def apply_md_override(
        self,
        action_dict: dict,
        baseline_load: float,
        md_limit_kw: float,
        battery_soc: float,
        bess_capacity_kwh: float,
        remaining_peak_ticks: int,
        max_discharge_kw: float,
        reserve_soc: float,
        tariff_window: str,
    ) -> dict:
        """Budget-aware MD override: force minimum discharge when load exceeds MD limit."""
        if (
            tariff_window != "PEAK"
            or baseline_load <= md_limit_kw
            or battery_soc <= reserve_soc + 0.05
        ):
            return action_dict

        available_kwh = max(0.0, (battery_soc - reserve_soc) * bess_capacity_kwh)
        max_sustainable_kw = available_kwh / (remaining_peak_ticks * 0.5)
        min_discharge_kw = min(
            baseline_load - md_limit_kw + 15.0,
            max_discharge_kw,
            max_sustainable_kw,
        )
        current_kw = action_dict.get("discharge_kw") or 0.0
        if action_dict.get("action") != "discharge" or current_kw < min_discharge_kw:
            return {
                "action": "discharge",
                "discharge_kw": min_discharge_kw,
                "charge_kw": None,
                "duration_min": 30,
            }
        return action_dict
