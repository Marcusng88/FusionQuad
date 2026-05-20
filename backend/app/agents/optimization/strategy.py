"""Canonical OptimizationStrategy model — single shape across planner, controller, solver."""
from pydantic import BaseModel


class OptimizationStrategy(BaseModel):
    strategy_name: str
    shave_kw: float
    reserve_soc_pct: float
    target_soc_end: float = 0.50
    rationale: str
    confidence: float
    md_limit_kw: float
