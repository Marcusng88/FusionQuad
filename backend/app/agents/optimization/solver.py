"""MILP solver for BESS optimal dispatch."""
from dataclasses import dataclass
from typing import Literal, Optional

import pulp

from app.agents.tariff.rates import get_energy_rate as _get_central_rate


@dataclass
class DispatchInterval:
    interval: int
    action: Literal["discharge", "charge", "hold"]
    discharge_kw: Optional[float] = None
    charge_kw: Optional[float] = None
    target_soc: Optional[float] = None
    expected_savings_rm: float = 0.0


@dataclass
class DispatchAction:
    action: Literal["discharge", "charge", "hold"]
    discharge_kw: Optional[float] = None
    charge_kw: Optional[float] = None
    duration_min: int = 30
    expected_soc_after: Optional[float] = None


@dataclass
class OptimizationResult:
    dispatch_plan: list
    current_dispatch_index: int
    dispatch_action: DispatchAction


@dataclass
class OptimizationInput:
    optimization_strategy: dict
    load_forecast: list
    tariff_window: str
    battery_soc: float
    bess_capacity_kwh: float
    md_limit_kw: float
    current_dispatch_index: int
    previous_dispatch_plan: Optional[list] = None


MAX_DISCHARGE_KW = 100.0
MAX_CHARGE_KW = 50.0
MIN_SOC = 0.20
MAX_SOC = 0.95
DT_SECONDS = 1800


class OptimizationSolver:
    def solve(self, input_data: OptimizationInput) -> OptimizationResult:
        if input_data.battery_soc < MIN_SOC:
            return self._force_hold(input_data)
        if not input_data.load_forecast:
            return self._empty_plan(input_data)
        if not input_data.optimization_strategy.get("strategy"):
            return self._conservative_fallback(input_data)
        try:
            return self._solve_milp(input_data)
        except Exception:
            return self._fallback_discharge(input_data)

    def _force_hold(self, input_data: OptimizationInput) -> OptimizationResult:
        return OptimizationResult(
            dispatch_plan=[DispatchInterval(interval=i, action="hold") for i in range(len(input_data.load_forecast))],
            current_dispatch_index=input_data.current_dispatch_index,
            dispatch_action=DispatchAction(action="hold"),
        )

    def _empty_plan(self, input_data: OptimizationInput) -> OptimizationResult:
        return OptimizationResult(
            dispatch_plan=[],
            current_dispatch_index=0,
            dispatch_action=DispatchAction(action="hold"),
        )

    def _conservative_fallback(self, input_data: OptimizationInput) -> OptimizationResult:
        discharge_kw = 50.0 if input_data.battery_soc > 0.30 else None
        action_type = "discharge" if discharge_kw else "hold"
        dispatch_plan = []
        soc = input_data.battery_soc
        for i, load in enumerate(input_data.load_forecast):
            if action_type == "discharge" and discharge_kw:
                energy_kwh = discharge_kw * (DT_SECONDS / 3600)
                soc = max(MIN_SOC, min(MAX_SOC, soc - energy_kwh / input_data.bess_capacity_kwh))
            dispatch_plan.append(DispatchInterval(
                interval=i,
                action=action_type,
                discharge_kw=discharge_kw if action_type == "discharge" else None,
                charge_kw=None,
                target_soc=soc,
                expected_savings_rm=self._estimate_savings(discharge_kw, input_data),
            ))
        return OptimizationResult(
            dispatch_plan=dispatch_plan,
            current_dispatch_index=input_data.current_dispatch_index,
            dispatch_action=DispatchAction(
                action=action_type,
                discharge_kw=discharge_kw,
                duration_min=30,
                expected_soc_after=soc,
            ),
        )

    def _solve_milp(self, input_data: OptimizationInput):
        n_intervals = len(input_data.load_forecast)
        strategy = input_data.optimization_strategy
        energy_rate = self._get_energy_rate(input_data.tariff_window)

        prob = pulp.LpProblem("BESS_Dispatch", pulp.LpMinimize)
        power = [pulp.LpVariable(f"power_{i}", -MAX_CHARGE_KW, MAX_DISCHARGE_KW) for i in range(n_intervals)]
        soc = [pulp.LpVariable(f"soc_{i}", MIN_SOC, MAX_SOC) for i in range(n_intervals)]

        energy_cost = sum(energy_rate * power[i] * (DT_SECONDS / 3600) for i in range(n_intervals))
        prob += energy_cost

        for i in range(n_intervals):
            prob += power[i] <= MAX_DISCHARGE_KW, f"max_discharge_{i}"
            prob += power[i] >= -MAX_CHARGE_KW, f"max_charge_{i}"
            if i == 0:
                prob += soc[i] == input_data.battery_soc, f"initial_soc_{i}"
            else:
                energy_kwh = power[i-1] * (DT_SECONDS / 3600)
                prob += soc[i] == soc[i-1] - (energy_kwh / input_data.bess_capacity_kwh), f"soc_dynamics_{i}"
            prob += input_data.load_forecast[i] - power[i] <= input_data.md_limit_kw, f"md_threshold_{i}"

        target_soc_end = strategy.get("target_soc_end", 0.50)
        reserve_soc_pct = strategy.get("reserve_soc_pct", 0.20)
        prob += soc[n_intervals - 1] >= target_soc_end, "target_soc_end"
        for i in range(n_intervals):
            prob += soc[i] >= reserve_soc_pct, f"reserve_soc_{i}"

        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=1)
        prob.solve(solver)

        if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):
            raise Exception(f"MILP infeasible: {pulp.LpStatus[prob.status]}")

        dispatch_plan = []
        for i in range(n_intervals):
            p_val = pulp.value(power[i]) or 0.0
            s_val = pulp.value(soc[i]) or input_data.battery_soc
            if p_val > 1.0:
                action = "discharge"
                d_kw = min(p_val, MAX_DISCHARGE_KW)
                c_kw = None
            elif p_val < -1.0:
                action = "charge"
                d_kw = None
                c_kw = min(-p_val, MAX_CHARGE_KW)
            else:
                action = "hold"
                d_kw = None
                c_kw = None
            dispatch_plan.append(DispatchInterval(
                interval=i,
                action=action,
                discharge_kw=d_kw,
                charge_kw=c_kw,
                target_soc=s_val,
                expected_savings_rm=self._estimate_savings(p_val, input_data),
            ))

        idx = min(input_data.current_dispatch_index, len(dispatch_plan) - 1)
        current = dispatch_plan[idx]
        return OptimizationResult(
            dispatch_plan=dispatch_plan,
            current_dispatch_index=input_data.current_dispatch_index,
            dispatch_action=DispatchAction(
                action=current.action,
                discharge_kw=current.discharge_kw,
                charge_kw=current.charge_kw,
                duration_min=30,
                expected_soc_after=current.target_soc,
            ),
        )

    def _fallback_discharge(self, input_data: OptimizationInput) -> OptimizationResult:
        shave_kw = input_data.optimization_strategy.get("shave_kw", 80.0)
        discharge_kw = min(shave_kw, MAX_DISCHARGE_KW)
        dispatch_plan = []
        soc = input_data.battery_soc
        for i, load in enumerate(input_data.load_forecast):
            energy_kwh = discharge_kw * (DT_SECONDS / 3600)
            new_soc = soc - energy_kwh / input_data.bess_capacity_kwh
            if new_soc < MIN_SOC:
                action = "hold"
                d_kw = None
                actual_soc = soc  # SOC doesn't change when holding
            else:
                action = "discharge"
                d_kw = discharge_kw
                actual_soc = new_soc
            dispatch_plan.append(DispatchInterval(
                interval=i,
                action=action,
                discharge_kw=d_kw,
                charge_kw=None,
                target_soc=actual_soc,
                expected_savings_rm=self._estimate_savings(d_kw, input_data),
            ))
            soc = actual_soc
        idx = min(input_data.current_dispatch_index, len(dispatch_plan) - 1)
        current = dispatch_plan[idx]
        return OptimizationResult(
            dispatch_plan=dispatch_plan,
            current_dispatch_index=input_data.current_dispatch_index,
            dispatch_action=DispatchAction(
                action=current.action,
                discharge_kw=current.discharge_kw,
                duration_min=30,
                expected_soc_after=current.target_soc,
            ),
        )

    def _get_energy_rate(self, tariff_window: str) -> float:
        return _get_central_rate("C2", tariff_window)

    def _estimate_savings(self, power_kw: Optional[float], input_data: OptimizationInput) -> float:
        if power_kw is None or power_kw <= 0:
            return 0.0
        return power_kw * (DT_SECONDS / 3600) * self._get_energy_rate(input_data.tariff_window)