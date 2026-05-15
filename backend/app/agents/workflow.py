"""LangGraph workflow - multi-agent orchestration with checkpointing."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.data_loader.node import data_loader_node
from app.agents.forecast import forecast_node
from app.agents.tariff.node import TariffNode
from app.agents.planner.node import planner_node
from app.agents.optimization import optimization_node
from app.agents.controller.node import controller_node
from app.agents.auditor.agent import auditor_node


def create_workflow() -> StateGraph:
    """Create the multi-agent energy management workflow."""
    builder = StateGraph(AgentState)

    tariff_node = TariffNode()

    # Add all agent nodes
    builder.add_node("data_loader", data_loader_node)
    builder.add_node("forecast", forecast_node)
    builder.add_node("tariff", tariff_node.invoke)
    builder.add_node("planner", planner_node)
    builder.add_node("optimization", optimization_node)
    builder.add_node("controller", controller_node)
    builder.add_node("auditor", auditor_node)

    # Define edges
    builder.add_edge(START, "data_loader")
    builder.add_edge("data_loader", "forecast")
    builder.add_edge("forecast", "tariff")
    builder.add_edge("tariff", "planner")
    builder.add_edge("planner", "optimization")
    builder.add_edge("optimization", "controller")
    builder.add_edge("controller", "auditor")
    builder.add_edge("auditor", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)