from fastapi import APIRouter

from app.api.v1.endpoints import health, simulation

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
