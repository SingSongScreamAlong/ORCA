"""Relationship endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, current_principal, pagination
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.schemas.relationship import RelationshipCreate, RelationshipRead
from app.services.relationship_service import RelationshipService

router = APIRouter(prefix="/relationships", tags=["relationships"])


def _service() -> RelationshipService:
    return RelationshipService()


@router.get("", response_model=list[RelationshipRead], summary="List relationships")
def list_relationships(
    page: Pagination = Depends(pagination),
    status_filter: ReviewStatus | None = Query(
        None, alias="status", description="Filter by relationship status."
    ),
) -> list[RelationshipRead]:
    return _service().list(limit=page.limit, offset=page.offset, status=status_filter)


@router.post(
    "",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a relationship",
)
def create_relationship(
    payload: RelationshipCreate,
    principal: Principal = Depends(current_principal),
) -> RelationshipRead:
    # Most relationships are created `proposed` and routed to the review queue.
    return _service().create(payload, principal)


@router.get("/{relationship_id}", response_model=RelationshipRead, summary="Get a relationship")
def get_relationship(relationship_id: UUID) -> RelationshipRead:
    return _service().get(relationship_id)
