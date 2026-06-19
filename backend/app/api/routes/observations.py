"""Observation endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, get_uow, pagination, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.observation import ObservationCreate, ObservationRead
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("", response_model=list[ObservationRead], summary="List observations")
def list_observations(
    page: Pagination = Depends(pagination),
    case_id: UUID | None = Query(None, description="Filter by case."),
    status_filter: ReviewStatus | None = Query(None, alias="status", description="Filter by status."),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ObservationRead]:
    return ObservationService(uow).list(
        limit=page.limit, offset=page.offset, case_id=case_id, status=status_filter
    )


@router.post(
    "",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Intake an observation (enters the review queue as proposed)",
)
def create_observation(
    payload: ObservationCreate,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> ObservationRead:
    return ObservationService(uow).intake(payload, principal)


@router.get("/{observation_id}", response_model=ObservationRead, summary="Get an observation")
def get_observation(
    observation_id: UUID,
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> ObservationRead:
    return ObservationService(uow).get(observation_id)
