"""Tariff agent - analyzes TNB tariff windows and rates."""

from datetime import datetime

from app.agents.state import AgentState


# TNB July 2025 tariff rates (from plan.md)
TARIFF_RATES = {
    "C2": {  # Medium Voltage Commercial TOU
        "peak_energy": 28.52,  # sen/kWh
        "off_peak_energy": 24.43,  # sen/kWh
        "capacity": 30.19,  # RM/kW
        "network": 66.87,  # RM/kW
    },
    "E2": {  # Medium Voltage Industrial TOU
        "peak_energy": 28.52,
        "off_peak_energy": 22.40,
        "capacity": 30.19,
        "network": 66.87,
    },
    "C1": {  # Medium Voltage General Commercial
        "peak_energy": 28.52,
        "off_peak_energy": 24.43,
        "capacity": 29.43,
        "network": 59.84,
    },
    "E1": {  # Medium Voltage General Industrial
        "peak_energy": 28.52,
        "off_peak_energy": 22.40,
        "capacity": 29.43,
        "network": 59.84,
    },
}

# Demand charge: RM 97.06/kW for C2/E2, RM 89.27/kW for C1/E1 (from plan.md)
DEMAND_RATES = {
    "C2": 97.06,
    "E2": 97.06,
    "C1": 89.27,
    "E1": 89.27,
}


def _get_tariff_window(dt: datetime) -> str:
    """Determine tariff window for a given datetime.

    Peak: 2PM-10PM weekdays
    Off-peak: 10PM-2PM weekdays
    Weekend: all day weekends/holidays
    """
    if dt.weekday() >= 5:  # Saturday, Sunday
        return "WEEKEND"
    hour = dt.hour
    if 14 <= hour < 22:  # 2PM - 10PM
        return "PEAK"
    return "OFF_PEAK"


def tariff_node(state: AgentState) -> dict:
    """Analyze current tariff window and rates.

    Determines tariff window based on current time and calculates
    applicable energy/demand rates.
    """
    now = datetime.now()

    tariff_window = _get_tariff_window(now)
    tariff_type = "C2"  # Default to MV Commercial TOU

    rates = TARIFF_RATES.get(tariff_type, TARIFF_RATES["C2"])
    demand_rate = DEMAND_RATES.get(tariff_type, DEMAND_RATES["C2"])

    if tariff_window == "PEAK":
        energy_rate = rates["peak_energy"]
    elif tariff_window == "WEEKEND":
        energy_rate = rates["off_peak_energy"]
    else:
        energy_rate = rates["off_peak_energy"]

    # Peak demand charge applies during any 30-min window in month
    # Off-peak MD is not charged for MV/HV customers (from plan.md)
    demand_charge = demand_rate if tariff_window == "PEAK" else 0.0

    return {
        "tariff_window": tariff_window,
        "energy_rate": energy_rate,
        "demand_charge": demand_charge,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Tariff analysis: {tariff_window} window. "
                    f"Energy: {energy_rate} sen/kWh, Demand: {demand_charge} RM/kW"
                ),
            }
        ],
    }