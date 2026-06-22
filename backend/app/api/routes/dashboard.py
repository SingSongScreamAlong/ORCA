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
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.common import ORCAModel
from app.schemas.hunting import IntelIdentifier
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.review import ReviewItemRead
from app.services.case_service import CaseService
from app.services.hunting_intel_service import HuntingIntelService
from app.services.hunting_registry_service import HuntingRegistryService
from app.services.observation_service import ObservationService
from app.services.relationship_service import RelationshipService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class Counts(ORCAModel):
    observations: int
    relationships: int
    pending_review: int
    cases: int


class SystemHealth(ORCAModel):
    status: str
    storage_backend: str


class HuntingPosture(ORCAModel):
    """Hunting Grounds at-a-glance for the operator's dashboard (the recon picture)."""

    monitored_sources: int
    total_sources: int
    aors: int
    leads: int
    cross_venue_links: int
    top_cross_venue: list[IntelIdentifier]


class DashboardSummary(ORCAModel):
    counts: Counts
    recent_observations: list[ObservationRead]
    recent_relationships: list[RelationshipRead]
    review_queue: list[ReviewItemRead]
    hunting: HuntingPosture
    system_health: SystemHealth


@router.get("/summary", response_model=DashboardSummary, summary="Dashboard summary")
def dashboard_summary(
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> DashboardSummary:
    settings = get_settings()
    # Everything is scoped to the caller's cases (administrators see all).
    observations = ObservationService(uow).list(limit=10_000, status=None, principal=principal)
    relationships = RelationshipService(uow).list(limit=10_000, status=None, principal=principal)
    review_queue = ReviewService(uow).list(limit=10_000, status=ReviewStatus.PROPOSED, principal=principal)
    cases = CaseService(uow).list(principal, limit=10_000)

    # Hunting Grounds recon posture (registry rollup + cross-venue intelligence).
    hsummary = HuntingRegistryService(uow).summary()
    intel = HuntingIntelService(uow).picture()

    return DashboardSummary(
        counts=Counts(
            observations=len(observations),
            relationships=len(relationships),
            pending_review=len(review_queue),
            cases=len(cases),
        ),
        recent_observations=observations[:5],
        recent_relationships=relationships[:5],
        review_queue=review_queue[:10],
        hunting=HuntingPosture(
            monitored_sources=hsummary.totals.monitored,
            total_sources=hsummary.totals.total,
            aors=len(hsummary.aors),
            leads=intel.leads,
            cross_venue_links=intel.cross_venue_count,
            top_cross_venue=intel.cross_venue[:5],
        ),
        system_health=SystemHealth(status="ok", storage_backend=settings.storage_backend),
    )
