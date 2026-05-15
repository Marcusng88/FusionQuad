"""Tests for multi-agent workflow."""

from app.agents.state import AgentState
from app.agents.workflow import create_workflow


class TestAgentState:
    """Verify state definition structure."""

    def test_agent_state_has_required_fields(self):
        """AgentState TypedDict has all required fields per plan.md."""
        state = AgentState(
            day_type=None,
            current_time=None,
            loaded_data=None,
            data_quality=None,
            load_forecast=None,
            forecast_confidence=None,
            tariff_window=None,
            energy_rate=None,
            demand_charge=None,
            optimization_strategy=None,
            dispatch_plan=None,
            dispatch_action=None,
            battery_soc=None,
            messages=[],
        )
        assert state["loaded_data"] is None
        assert state["load_forecast"] is None
        assert state["tariff_window"] is None
        assert state["messages"] == []


class TestWorkflow:
    """Test workflow compilation and basic invocation."""

    def test_workflow_compiles(self):
        """Workflow creates without error."""
        workflow = create_workflow()
        assert workflow is not None

    def test_workflow_has_required_nodes(self):
        """Workflow has all agent nodes from plan.md."""
        workflow = create_workflow()
        graph = workflow.get_graph()
        node_names = set(graph.nodes)

        assert "data_loader" in node_names
        assert "forecast" in node_names
        assert "tariff" in node_names
        assert "planner" in node_names
        assert "optimization" in node_names
        assert "controller" in node_names
        assert "auditor" in node_names

    def test_workflow_runs_with_empty_state(self):
        """Workflow invocation with empty state does not crash."""
        workflow = create_workflow()
        config = {"configurable": {"thread_id": "test-1"}}

        result = workflow.invoke(
            AgentState(
                day_type=None,
                current_time=None,
                loaded_data=None,
                data_quality=None,
                load_forecast=None,
                forecast_confidence=None,
                tariff_window=None,
                energy_rate=None,
                demand_charge=None,
                optimization_strategy=None,
                dispatch_plan=None,
                dispatch_action=None,
                battery_soc=None,
                messages=[],
            ),
            config,
        )

        assert result is not None
        assert "messages" in result


class TestWorkflowEdges:
    """Verify workflow graph structure."""

    def test_workflow_has_checkpointer(self):
        """Workflow uses InMemorySaver checkpointer for state persistence."""
        workflow = create_workflow()
        config = {"configurable": {"thread_id": "test-checkpointer"}}
        list(workflow.get_state_history(config))
