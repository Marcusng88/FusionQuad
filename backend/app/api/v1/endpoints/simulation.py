from fastapi import APIRouter, Depends, Request

from app.schemas.simulation import (
    PlaySimulationRequest,
    SimulationSessionRequest,
    SimulationStateResponse,
    StartSimulationRequest,
)
from app.services.simulation import SimulationService

router = APIRouter()


def get_simulation_service(request: Request) -> SimulationService:
    return request.app.state.simulation_service


@router.post("/start", response_model=SimulationStateResponse, summary="Start a simulation")
async def start_simulation(
    payload: StartSimulationRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.start(
        day_type=payload.day_type,
        bess_capacity_kwh=payload.bess_capacity_kwh,
        battery_soc=payload.battery_soc,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )


@router.post("/step", response_model=SimulationStateResponse, summary="Advance one simulation interval")
async def step_simulation(
    payload: SimulationSessionRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.step(payload.session_id)


@router.post("/play", response_model=SimulationStateResponse, summary="Enable autoplay for a simulation")
async def play_simulation(
    payload: PlaySimulationRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.play(payload.session_id, interval_seconds=payload.interval_ms / 1000)


@router.post("/pause", response_model=SimulationStateResponse, summary="Pause autoplay for a simulation")
async def pause_simulation(
    payload: SimulationSessionRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.pause(payload.session_id)


@router.get("/state", response_model=SimulationStateResponse, summary="Get current simulation state")
async def get_simulation_state(
    session_id: str,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.get_state(session_id)
