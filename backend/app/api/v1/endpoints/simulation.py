import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.schemas.simulation import (
    ScenarioMetadataResponse,
    SimulationSessionRequest,
    SimulationStateResponse,
    StartSimulationRequest,
)
from app.services.simulation import SimulationService

router = APIRouter()


def get_simulation_service(request: Request) -> SimulationService:
    return request.app.state.simulation_service


@router.get("/scenarios/{day_type}/metadata", response_model=ScenarioMetadataResponse, summary="Get scenario metadata without starting simulation")
async def get_scenario_metadata(
    day_type: str,
    service: SimulationService = Depends(get_simulation_service),
) -> ScenarioMetadataResponse:
    return await service.get_scenario_metadata(day_type)


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
        forecast_model=payload.forecast_model,
    )


@router.post("/step", response_model=SimulationStateResponse, summary="Advance one simulation interval")
async def step_simulation(
    payload: SimulationSessionRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.step(payload.session_id)


@router.post("/run", response_model=SimulationStateResponse, summary="Run all simulation intervals to completion")
async def run_simulation(
    payload: SimulationSessionRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.run(payload.session_id)


@router.get("/state", response_model=SimulationStateResponse, summary="Get current simulation state")
async def get_simulation_state(
    session_id: str,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationStateResponse:
    return await service.get_state(session_id)


@router.get("/stream/{session_id}", summary="Stream full simulation run via SSE")
async def stream_simulation(
    session_id: str,
    service: SimulationService = Depends(get_simulation_service),
) -> StreamingResponse:
    async def event_generator():
        async for chunk in service.run_stream(session_id):
            event = chunk["event"]
            data = json.dumps(chunk["data"], default=str)
            yield f"event: {event}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
