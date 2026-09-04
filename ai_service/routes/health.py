"""
Health check endpoints.
"""

from fastapi import APIRouter
from ai_service.config import get_settings
from ai_service.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Root health probe")
@router.get("/api/v1/health", response_model=HealthResponse, summary="Versioned health probe")
async def get_health():
    """Returns application health status and environment metadata."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        environment=settings.AI_SERVICE_ENV,
    )
