"""
Standardized error response schemas.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Predictable API error structure avoiding stack trace leakage."""

    error: str = Field(description="High level error type category")
    message: str = Field(description="Human readable explanation")
    details: Optional[List[Any]] = Field(
        default=None, description="Detailed field-level validation errors if available"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of error event",
    )
