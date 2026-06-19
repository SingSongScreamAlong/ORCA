"""Dashboard summary endpoint.

Answers the three questions the dashboard exists to answer: what is new, what
changed, and what requires review — plus a system-health snapshot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_uow, require
from app.core.config import get_settings
from app.core.rbac import Capability
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.common import ORCAModel
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.review import ReviewItemRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class Counts(ORCAModel):
    observations: int
    relationships: int
    pending_review: int
    cases: int


class SystemHealth(ORCAModel):
    status: str
    storage_backend: str


class DashboardSummary(ORCAModel):
    counts: Counts
    recent_observations: list[ObservationRead]
    recent_relationships: list[RelationshipRead]
    review_queue: list[ReviewItemRead]
    system_health: SystemHealth


@router.get("/summary", response_model=DashboardSummary, summary="Dashboard summary")
def dashboard_summary(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> DashboardSummary:
    settings = get_settings()
    return DashboardSummary(
        counts=Counts(
            observations=len(uow.observations.list(limit=10_000, status=None)),
            relationships=len(uow.relationships.list(limit=10_000, status=None)),
            pending_review=uow.reviews.pending_count(),
            cases=len(uow.cases.list(limit=10_000)),
        ),
        recent_observations=uow.observations.list(limit=5, status=None),
        recent_relationships=uow.relationships.list(limit=5, status=None),
        review_queue=uow.reviews.list(limit=10),
        system_health=SystemHealth(status="ok", storage_backend=settings.storage_backend),
    )
