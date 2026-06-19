"""Health endpoint.

Reports liveness and the configured storage backend. In the database backend this is
where store reachability checks would be surfaced for the dashboard's System Health
panel.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import ORCAModel

router = APIRouter(tags=["system"])


class HealthResponse(ORCAModel):
    status: str
    service: str
    version: str
    storage_backend: str


@router.get("/health", response_model=HealthResponse, summary="Liveness and backend info")
def health() -> HealthResponse:
    settings = get_settings()
    from app import __version__

    return HealthResponse(
        status="ok",
        service=settings.project_name,
        version=__version__,
        storage_backend=settings.storage_backend,
    )
