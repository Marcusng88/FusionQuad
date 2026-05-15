"""Planner Agent - GridWise AI"""
from pathlib import Path
from typing import Any

STRATEGIES_DIR = Path(__file__).parent.parent.parent.parent / "strategies"
EXPERIENCE_DIR = Path(__file__).parent.parent.parent.parent / "experience"


def search_guidelines(query: str) -> list[dict[str, Any]]:
    """Search strategy and experience files for matching guidelines."""
    if not query or not query.strip():
        return []

    keywords = query.lower().split()
    results = []

    for dirname in [STRATEGIES_DIR, EXPERIENCE_DIR]:
        if not dirname.exists():
            continue
        for filepath in dirname.glob("*.md"):
            content = filepath.read_text()
            if any(kw in content.lower() for kw in keywords):
                results.append({
                    "content": content[:500],
                    "source": filepath.name,
                    "dir": filepath.parent.name,
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
    """Build context string from AgentState value objects."""
    if not state:
        return ""

    parts = []

    tariff = state.get("tariff") or {}
    if window := tariff.get("window"):
        parts.append(f"Tariff Window: {window}")

    if day_type := state.get("day_type"):
        parts.append(f"Day Type: {day_type}")

    battery = state.get("battery") or {}
    if soc := battery.get("soc"):
        parts.append(f"Battery SOC: {soc}%")
    if cycles := battery.get("cycle_count"):
        parts.append(f"Cycle Count: {cycles}")

    forecast = state.get("forecast") or {}
    if load := forecast.get("load_forecast"):
        parts.append(f"Load Forecast: {load} kW")
    if confidence := forecast.get("confidence"):
        parts.append(f"Forecast Confidence: {confidence}")

    if time := state.get("current_time"):
        parts.append(f"Current Time: {time}")

    return "\n".join(parts) if parts else ""


def run_planner_tick(agent, state: dict[str, Any]) -> dict[str, Any]:
    """Execute single planner tick with agent and state."""
    context = get_forecast_context(state)
    tariff = state.get("tariff") or {}
    results = search_guidelines(f"{tariff.get('window', '')} {state.get('day_type', '')}")
    
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
