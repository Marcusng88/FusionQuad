# SKILL: FusionQuad BESS Strategy Planner

## Name
bess_strategy_planner

## Description
The FusionQuad BESS Strategy Planner selects the optimal dispatch strategy based on tariff windows, day type, forecast data, and battery state. It uses semantic search over strategy guideline files to find the most relevant strategy for the current operating context.

## When to Use
Invoke this skill when you need to:
1. Determine the optimal BESS dispatch strategy for a given time period
2. Understand which strategy rules apply given current tariff window and day type
3. Calculate appropriate discharge targets and reserve SOC levels
4. Apply cross-cutting BESS safety guidelines to strategy recommendations

## Available Strategies
- **aggressive_peak_shaving**: Weekday PEAK tariff strategy for maximizing cost savings
- **holiday_surge**: Elevated-load holiday strategy with conservative discharge
- **solar_duck_curve**: Two-phase strategy for solar-heavy grid environments
- **offpeak_valley_fill**: Overnight/low-tariff charging strategy
- **general_bess_guidelines**: Mandatory BESS safety and lifecycle rules

## Tools Available
- `search_guidelines(query)`: Semantic search over strategy files
- `read_guideline_file(path)`: Read full content of a specific strategy file
- `get_forecast_context()`: Get formatted forecast summary for context

## How to Use
1. First call `search_guidelines` with a query combining tariff_window, day_type, and load profile
2. Read the top-ranked strategy file(s)
3. Check `general_bess_guidelines.md` for mandatory safety constraints
4. Apply strategy rules based on current BESS SOC and cycle count
5. Output the optimization_strategy dict

## Output Format
The planner outputs an `optimization_strategy` dict containing:
- `strategy_name`: Identifying name of selected strategy
- `targets`: Dict with `shave_kw` and `reserve_soc_pct` targets
- `constraints`: List of constraint strings to apply
- `rationale`: Human-readable explanation of strategy selection
- `md_limit_kw`: Market door limit from system config
- `confidence`: Forecast confidence for downstream optimization

## Example Queries
- "peak weekday aggressive shaving 80kW forecast"
- "holiday surge load 50kW SOC 60%"
- "solar duck curve morning valley afternoon ramp"
- "offpeak valley fill overnight charge weekday"
