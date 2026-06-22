"""ORCA backend application entry point.

Creates the FastAPI app, configures CORS, maps domain errors to HTTP responses, and
mounts the API under the configured prefix.

Run locally with:

    uvicorn app.main:app --reload
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings
from app.core.security import AuthenticationError
from app.services.errors import NotFoundError, PermissionDenied, ValidationError


@contextlib.asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start the continuous discovery cadence on startup, stop it on shutdown.

    The scheduler is disabled by default and ``start()`` is a no-op unless
    ``ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED`` is set, so this is inert in dev/CI.
    """
    from app.services.hunting_scheduler import scheduler

    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ORCA API",
        version=__version__,
        description=(
            "ORCA preserves observations, discovers relationships, and maintains "
            "institutional intelligence memory. The system proposes; analysts decide."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", tags=["system"], summary="Service root")
    def root() -> dict[str, str]:
        return {
            "service": settings.project_name,
            "version": __version__,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Map service-layer domain errors to HTTP responses."""

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(PermissionDenied)
    async def _permission(_: Request, exc: PermissionDenied) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(AuthenticationError)
    async def _auth(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})


app = create_app()
