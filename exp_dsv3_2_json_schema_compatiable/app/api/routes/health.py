"""
Health check endpoints.
"""
from datetime import datetime
from fastapi import APIRouter

from app.models.responses import HealthResponse
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is running and healthy"
)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version
    )
