"""Routes package."""

from ai_service.routes.documents import router as documents_router
from ai_service.routes.health import router as health_router

__all__ = ["health_router", "documents_router"]
