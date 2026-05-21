"""LangGraph workflow - multi-agent orchestration."""

from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.data_loader.node import data_loader_node
from app.agents.forecast import forecast_node
from app.agents.tariff.node import TariffNode
from app.agents.planner.node import planner_node
from app.agents.controller.node import controller_node
from app.agents.auditor.agent import auditor_node


def _route_after_controller(state: AgentState) -> str:
    """Route back to planner if controller rejected the plan, else proceed to auditor."""
    return "planner" if state.get("rejection_reason") is not None else "auditor"


def create_workflow() -> StateGraph:
    """Create the multi-agent energy management workflow."""
    builder = StateGraph(AgentState)

    tariff_node = TariffNode()

    builder.add_node("data_loader", data_loader_node)
    builder.add_node("forecast", forecast_node)
    builder.add_node("tariff", tariff_node.invoke)
    builder.add_node("planner", planner_node)
    builder.add_node("controller", controller_node)
    builder.add_node("auditor", auditor_node)

    builder.add_edge(START, "data_loader")
    builder.add_edge("data_loader", "forecast")
    builder.add_edge("data_loader", "tariff")
    builder.add_edge("forecast", "planner")
    builder.add_edge("tariff", "planner")
    builder.add_edge("planner", "controller")
    builder.add_conditional_edges("controller", _route_after_controller, {"planner": "planner", "auditor": "auditor"})
    builder.add_edge("auditor", END)

    return builder.compile()
