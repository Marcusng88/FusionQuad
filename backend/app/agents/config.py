"""Centralized agent model configuration.

Override any model via env var: PLANNER_MODEL, CONTROLLER_MODEL, AUDITOR_MODEL.
"""

import os

_DEFAULT = "claude-sonnet-4-6"

AGENT_MODELS: dict[str, str] = {
    "planner":    os.getenv("PLANNER_MODEL",    _DEFAULT),
    "controller": os.getenv("CONTROLLER_MODEL", _DEFAULT),
    "auditor":    os.getenv("AUDITOR_MODEL",    _DEFAULT),
}
