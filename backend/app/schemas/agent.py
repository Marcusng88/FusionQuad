from datetime import datetime
from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    tariff_window: str | None
    energy_rate: float | None
    demand_charge: float | None
    tariff_type: str | None
    current_time: datetime | None
