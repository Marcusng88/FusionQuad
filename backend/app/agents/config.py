"""Centralized agent configuration.

Override any model via env var: PLANNER_MODEL, CONTROLLER_MODEL, AUDITOR_MODEL.
"""

import os

_DEFAULT = "claude-sonnet-4-6"

AGENT_MODELS: dict[str, str] = {
    "planner":    os.getenv("PLANNER_MODEL",    _DEFAULT),
    "controller": os.getenv("CONTROLLER_MODEL", _DEFAULT),
    "auditor":    os.getenv("AUDITOR_MODEL",    _DEFAULT),
}

# ---------------------------------------------------------------------------
# BESS physical constants — single source of truth across all agent nodes.
# Changing a value here propagates to solver, controller, and planner.
# ---------------------------------------------------------------------------
MIN_SOC = 0.20       # hard floor: hold-only below this
RESERVE_SOC = 0.25   # soft reserve: MD override threshold base
MAX_SOC = 0.95       # charge ceiling
MAX_CHARGE_KW = 50.0 # conservative charge rate (0.05C for 1000 kWh)
PEAK_END_HOUR = 22   # TNB C2: PEAK window ends at 22:00
