"""
Health check response schemas.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Structured response for service health probes."""

    status: str = Field(default="ok", description="Service health state")
    service: str = Field(description="Name of the running service")
    version: str = Field(description="Semver version of the service")
    environment: str = Field(description="Deployment environment")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Current UTC timestamp",
    )
