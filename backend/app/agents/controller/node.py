"""Controller node that executes dispatch actions via a mock inverter tool."""

from __future__ import annotations

import os
from typing import Any

from deepagents import create_deep_agent
from langchain.tools import tool

from app.agents.state import AgentState
from app.core.model_selection import resolve_deepagents_model

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_CONTROLLER_PROMPT = """You are the Controller Agent for FusionQuad — you execute BESS dispatch actions.

Your task:
1. Read the current dispatch_action from state
2. Call mock_inverter_dispatch with correct parameters
3. Observe the response (new_soc, temp, cycle_count)
4. Write dispatch_result to state

Safety rules:
- If dispatch_action is None or "hold", do not call inverter — just log "hold"
- If battery_soc < 0.20 before dispatch, call "hold" instead and log "SOC too low — preserving"
"""


@tool
def mock_inverter_dispatch(
    action: str,
    power_kw: float,
    duration_min: int,
    current_soc: float,
    bess_capacity_kwh: float,
    temperature_c: float,
) -> dict[str, Any]:
    """Mock smart inverter dispatch — simulates BESS response."""
    efficiency_loss_pct = 0.05
    if action == "discharge":
        energy_kwh = power_kw * (duration_min / 60)
        actual_discharge = energy_kwh * (1 - efficiency_loss_pct)
        new_soc = current_soc - (actual_discharge / bess_capacity_kwh)
        temp_increase = 0.5 * (power_kw / 100)
        cycle_increment = energy_kwh / bess_capacity_kwh
        actual_kw = power_kw
    elif action == "charge":
        energy_kwh = power_kw * (duration_min / 60)
        new_soc = min(current_soc + (energy_kwh / bess_capacity_kwh), 0.95)
        temp_increase = 0.2 * (power_kw / 100)
        cycle_increment = -0.005
        actual_kw = power_kw
    else:
        new_soc = current_soc
        temp_increase = 0.1
        cycle_increment = 0.0
        actual_kw = 0.0

    return {
        "new_soc": new_soc,
        "temp_increase_c": temp_increase,
        "cycle_count_increment": cycle_increment,
        "action_taken": action,
        "actual_discharge_kw": actual_kw,
        "efficiency_loss_pct": efficiency_loss_pct,
    }


def _deep_agent_enabled(state: AgentState) -> bool:
    if state.get("use_deep_agent") is True:
        return True
    flag = os.getenv("DEEPAGENTS_ENABLED", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _build_controller_agent() -> Any:
    model = resolve_deepagents_model(_DEFAULT_MODEL)
    return create_deep_agent(
        name="controller-agent",
        model=model,
        system_prompt=_CONTROLLER_PROMPT,
        tools=[mock_inverter_dispatch],
    )


_CONTROLLER_AGENT: Any | None = None


def _get_controller_agent() -> Any:
    global _CONTROLLER_AGENT
    if _CONTROLLER_AGENT is None:
        _CONTROLLER_AGENT = _build_controller_agent()
    return _CONTROLLER_AGENT


def _run_dispatch(state: AgentState) -> tuple[dict[str, Any], float, float, float]:
    dispatch_action = state.get("dispatch_action") or {}
    action = dispatch_action.get("action", "hold")
    duration_min = dispatch_action.get("duration_min", 30)

    battery_soc = state.get("battery_soc", 0.50)
    bess_capacity_kwh = state.get("bess_capacity_kwh", 500.0)
    temperature_c = state.get("temperature_c", 30.0)

    power_kw = 0.0
    if action == "discharge":
        power_kw = dispatch_action.get("discharge_kw", 0.0) or 0.0
    elif action == "charge":
        power_kw = dispatch_action.get("charge_kw", 0.0) or 0.0

    if battery_soc < 0.20:
        action = "hold"
        power_kw = 0.0

    result = mock_inverter_dispatch(
        action=action,
        power_kw=power_kw,
        duration_min=duration_min,
        current_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        temperature_c=temperature_c,
    )

    new_soc = result.get("new_soc", battery_soc)
    new_temp = temperature_c + result.get("temp_increase_c", 0.0)
    new_cycle = state.get("cycle_count", 0.0) + result.get("cycle_count_increment", 0.0)

    return result, new_soc, new_cycle, new_temp


def controller_node(state: AgentState) -> dict:
    """Execute dispatch_action and update SOC, temperature, and cycle count."""
    dispatch_result, new_soc, new_cycle, new_temp = _run_dispatch(state)

    baseline_load = state.get("baseline_load")
    if baseline_load is None:
        baseline_load = state.get("forecast_kw", 0.0)

    actual_load = baseline_load
    if dispatch_result.get("action_taken") == "discharge":
        actual_load = max(0.0, baseline_load - dispatch_result.get("actual_discharge_kw", 0.0))
    elif dispatch_result.get("action_taken") == "charge":
        actual_load = baseline_load + dispatch_result.get("actual_discharge_kw", 0.0)

    current_index = state.get("current_dispatch_index", 0)
    next_index = current_index + 1

    messages: list[dict[str, str]] = []
    if _deep_agent_enabled(state):
        prompt = (
            f"Dispatch action: {state.get('dispatch_action')}\n"
            f"SOC before: {state.get('battery_soc', 0.5):.2f}\n"
            f"SOC after: {new_soc:.2f}"
        )
        try:
            agent = _get_controller_agent()
            result = agent.invoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": "controller"}},
            )
            if isinstance(result, dict):
                response = result.get("messages", [])
                if response:
                    messages.append({"role": "assistant", "content": str(response[-1].content)})
        except Exception:
            pass

    return {
        "dispatch_result": dispatch_result,
        "battery_soc": new_soc,
        "cycle_count": new_cycle,
        "temperature_c": new_temp,
        "last_dispatch_kw": dispatch_result.get("actual_discharge_kw", 0.0),
        "last_dispatch_duration_min": state.get("dispatch_action", {}).get("duration_min", 30),
        "current_dispatch_index": next_index,
        "baseline_load": baseline_load,
        "actual_load": actual_load,
        "messages": messages,
    }
