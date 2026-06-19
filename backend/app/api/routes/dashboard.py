"""Dashboard summary endpoint.

Answers the three questions the dashboard exists to answer: what is new, what
changed, and what requires review — plus a system-health snapshot.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import ORCAModel
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.review import ReviewItemRead
from app.services.observation_service import ObservationService
from app.services.relationship_service import RelationshipService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class Counts(ORCAModel):
    observations: int
    relationships: int
    pending_review: int


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
def dashboard_summary() -> DashboardSummary:
    observations = ObservationService()
    relationships = RelationshipService()
    reviews = ReviewService()
    settings = get_settings()

    recent_observations = observations.list(limit=5, offset=0)
    recent_relationships = relationships.list(limit=5, offset=0)
    queue = reviews.list(limit=10, offset=0)

    return DashboardSummary(
        counts=Counts(
            observations=len(observations.list(limit=10_000)),
            relationships=len(relationships.list(limit=10_000)),
            pending_review=reviews.pending_count(),
        ),
        recent_observations=recent_observations,
        recent_relationships=recent_relationships,
        review_queue=queue,
        system_health=SystemHealth(status="ok", storage_backend=settings.storage_backend),
    )
