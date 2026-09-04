"""
Main FastAPI Application Entry Point for AI/Data Service.
Configures middleware, routes, predictable error handling, and structured logging.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_service.config import get_settings
from ai_service.logging_config import logger
from ai_service.routes.documents import router as documents_router
from ai_service.routes.freshness import router as freshness_router
from ai_service.routes.health import router as health_router
from ai_service.routes.scoring import router as scoring_router
from ai_service.schemas.errors import ErrorResponse




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan management."""
    settings = get_settings()
    logger.info(
        f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION} "
        f"[env={settings.AI_SERVICE_ENV}, host={settings.AI_SERVICE_HOST}, port={settings.AI_SERVICE_PORT}]"
    )
    yield
    logger.info(f"Stopping {settings.SERVICE_NAME}")


def create_app() -> FastAPI:
    """Application factory for FastAPI AI/Data Service."""
    settings = get_settings()

    app = FastAPI(
        title="Jaldhaara Foundation AI/Data Service",
        description="Foundation for processing and analyzing CSR donor documents",
        version=settings.SERVICE_VERSION,
        lifespan=lifespan,
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"{method} {path} - {response.status_code} ({duration_ms}ms)")
        return response

    # Exception Handler: Pydantic Validation Error (HTTP 422)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
        err_res = ErrorResponse(
            error="Validation Error",
            message="The request payload failed schema validation",
            details=jsonable_encoder(exc.errors()),
        )
        return JSONResponse(
            status_code=422,
            content=err_res.model_dump(),
        )

    # Exception Handler: HTTP Exception
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
        err_res = ErrorResponse(
            error=f"HTTP {exc.status_code}",
            message=str(exc.detail),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=err_res.model_dump(),
        )

    # Exception Handler: Unhandled Internal Server Error (HTTP 500)
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
        err_res = ErrorResponse(
            error="Internal Server Error",
            message="An unexpected internal error occurred while processing the request",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=err_res.model_dump(),
        )

    # Include Routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(freshness_router)
    app.include_router(scoring_router)

    return app




app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_settings()
    uvicorn.run(
        "ai_service.main:app",
        host=config.AI_SERVICE_HOST,
        port=config.AI_SERVICE_PORT,
        reload=(config.AI_SERVICE_ENV == "development"),
    )
