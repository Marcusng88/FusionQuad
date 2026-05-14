"""LangGraph workflow - wires up all 5 agents with fan-out/fan-in and checkpointing."""

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.data_loader import data_loader_node
from app.agents.forecast import forecast_node
from app.agents.tariff import tariff_node
from app.agents.optimization import optimization_node
from app.agents.report import report_node


def should_continue(state: AgentState) -> Literal["report", "__end__"]:
    """Route to report node after optimization, or end if no data."""
    if state.get("load_forecast"):
        return "report"
    return END


def create_workflow() -> StateGraph:
    """Create the multi-agent energy management workflow.

    Architecture based on plan.md:
    - DataLoader: loads and validates CSV energy data
    - Forecast: generates load forecasts using GRU model
    - Tariff: analyzes current TNB tariff windows and rates
    - Optimization: generates BESS dispatch plan
    - Report: compiles final analysis report

    Flow: START -> data_loader -> [forecast, tariff] (parallel)
          -> optimization -> report -> END
    """
    builder = StateGraph(AgentState)

    # Add all agent nodes
    builder.add_node("data_loader", data_loader_node)
    builder.add_node("forecast", forecast_node)
    builder.add_node("tariff", tariff_node)
    builder.add_node("optimization", optimization_node)
    builder.add_node("report", report_node)

    # Define edges
    builder.add_edge(START, "data_loader")

    # Fan-out: forecast and tariff run in parallel after data loading
    builder.add_edge("data_loader", "forecast")
    builder.add_edge("data_loader", "tariff")

    # Fan-in: optimization waits for both forecast and tariff
    builder.add_edge("forecast", "optimization")
    builder.add_edge("tariff", "optimization")

    # Conditional routing to report
    builder.add_conditional_edges(
        "optimization",
        should_continue,
    )

    # Report leads to END
    builder.add_edge("report", END)

    # Compile with checkpointing for state persistence
    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)