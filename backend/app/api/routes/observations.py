"""Observation endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Pagination, current_principal, pagination
from app.core.security import Principal
from app.schemas.observation import ObservationCreate, ObservationRead
from app.services.observation_service import ObservationService

router = APIRouter(prefix="/observations", tags=["observations"])


def _service() -> ObservationService:
    return ObservationService()


@router.get("", response_model=list[ObservationRead], summary="List observations")
def list_observations(page: Pagination = Depends(pagination)) -> list[ObservationRead]:
    return _service().list(limit=page.limit, offset=page.offset)


@router.post(
    "",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an observation",
)
def create_observation(
    payload: ObservationCreate,
    principal: Principal = Depends(current_principal),
) -> ObservationRead:
    return _service().create(payload, principal)


@router.get("/{observation_id}", response_model=ObservationRead, summary="Get an observation")
def get_observation(observation_id: UUID) -> ObservationRead:
    return _service().get(observation_id)
