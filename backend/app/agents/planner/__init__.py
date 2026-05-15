"""Planner Agent - GridWise AI"""
from pathlib import Path
from typing import Any

STRATEGIES_DIR = Path(__file__).parent.parent.parent.parent / "strategies"


def search_guidelines(query: str) -> list[dict[str, Any]]:
    """Search strategy files for matching guidelines."""
    if not query or not query.strip():
        return []
    
    keywords = query.lower().split()
    results = []
    
    if not STRATEGIES_DIR.exists():
        return results
    
    for filepath in STRATEGIES_DIR.glob("*.md"):
        content = filepath.read_text()
        if any(kw in content.lower() for kw in keywords):
            results.append({
                "content": content[:500],
                "source": filepath.name
            })
    
    return results


def read_guideline_file(path: str) -> str:
    """Read a specific guideline file by name or path."""
    if not path:
        return ""
    
    # Try direct path
    filepath = Path(path)
    if not filepath.is_absolute() and not filepath.exists():
        filepath = STRATEGIES_DIR / path
    
    if filepath.exists():
        return filepath.read_text()
    return ""


def get_forecast_context(state: dict[str, Any]) -> str:
    """Build context string from AgentState fields."""
    if not state:
        return ""
    
    parts = []
    
    if tariff := state.get("tariff_window"):
        parts.append(f"Tariff Window: {tariff}")
    if day_type := state.get("day_type"):
        parts.append(f"Day Type: {day_type}")
    if soc := state.get("battery_soc"):
        parts.append(f"Battery SOC: {soc}%")
    if load := state.get("load_forecast"):
        parts.append(f"Load Forecast: {load} kW")
    if confidence := state.get("forecast_confidence"):
        parts.append(f"Forecast Confidence: {confidence}")
    if cycles := state.get("cycle_count"):
        parts.append(f"Cycle Count: {cycles}")
    if time := state.get("current_time"):
        parts.append(f"Current Time: {time}")
    
    return "\n".join(parts) if parts else ""


def run_planner_tick(agent, state: dict[str, Any]) -> dict[str, Any]:
    """Execute single planner tick with agent and state."""
    context = get_forecast_context(state)
    results = search_guidelines(f"{state.get('tariff_window', '')} {state.get('day_type', '')}")
    
    guidelines_text = "\n\n".join(
        f"=== {r['source']} ===\n{r['content']}" for r in results
    )
    
    prompt = f"""Based on the following state and guidelines, select the optimal BESS strategy.

STATE:
{context}

GUIDELINES:
{guidelines_text}

Respond with strategy selection in JSON format."""

    response = agent.run(prompt)
    
    if isinstance(response, dict):
        return response
    
    return {
        "strategy_name": "general_bess_guidelines",
        "targets": {"shave_kw": 0, "reserve_soc_pct": 20},
        "constraints": [],
        "rationale": "Default fallback strategy",
        "md_limit_kw": 50,
        "confidence": 0.5
    }
