"""Multi-agent orchestration for energy management."""

from app.agents.state import AgentState


def create_workflow(*args, **kwargs):
    from app.agents.workflow import create_workflow as _create_workflow
    return _create_workflow(*args, **kwargs)


__all__ = ["AgentState", "create_workflow"]
