# General BESS Guidelines

## Purpose
Cross-cutting rules for BESS operation that apply regardless of tariff window or day type.

## State of Charge (SOC) Limits
- **Hard Minimum**: 10% SOC — BESS protection cutoff, never discharge below this
- **Soft Minimum**: 20% SOC — Recommended reserve for emergency demand response
- **Charge Target**: 90-95% for normal full charge cycle
- **Charge Ceiling**: 100% SOC — Absolute maximum, do not over-charge

## Cycle Count Thresholds
- **0-2000 cycles**: Normal operation — full charge/discharge cycles permitted
- **2000-3000 cycles**: Reduced depth of discharge — limit to 80% DoD
- **3000+ cycles**: Conservative operation — limit to 50% DoD, preserve remaining cycle life
- **4000+ cycles**: End-of-life consideration — evaluate replacement timeline

## Depth of Discharge (DoD) Guidelines
- **Full DoD (100%)**: Permitted only during critical peak events and SOC > 70%
- **80% DoD**: Standard operating mode during high-value tariff windows
- **50% DoD**: Conservative mode for normal PEAK shaving
- **25% DoD**: Minimum discharge for light grid support

## Temperature Considerations
- **Below 0C**: Reduce charge/discharge rates by 50%
- **Below -10C**: Suspend all BESS operations (safety mode)
- **Above 40C**: Reduce charge/discharge rates by 30%
- **Above 45C**: Suspend all BESS operations (safety mode)

## Emergency Rules (Always Apply)
1. Never discharge below 10% SOC
2. Never charge above 100% SOC
3. If BESS experiences fault, go to IDLE mode immediately
4. If grid frequency drops below 59.5 Hz, disconnect and idle
5. If grid frequency rises above 60.5 Hz, disconnect and idle

## Lifecycle Preservation
- Avoid sustained high-rate charge/discharge cycles
- Allow periodic rest periods (1-2 hours per day at 50% SOC)
- Monthly equalization charges to balance cell voltages

## Priority
**MANDATORY** — These guidelines override all other strategy rules in case of conflict.
