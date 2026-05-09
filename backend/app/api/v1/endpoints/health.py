from fastapi import APIRouter

from app.schemas.health import HealthCheckResponse

router = APIRouter()


@router.get("", response_model=HealthCheckResponse, summary="Health check")
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", service="backend", version="v1")
