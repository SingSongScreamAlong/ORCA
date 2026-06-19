"""Relationship endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Pagination, current_principal, get_uow, pagination
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.relationship import RelationshipCreate, RelationshipRead
from app.services.relationship_service import RelationshipService

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.get("", response_model=list[RelationshipRead], summary="List relationships")
def list_relationships(
    page: Pagination = Depends(pagination),
    case_id: UUID | None = Query(None, description="Filter by case."),
    status_filter: ReviewStatus | None = Query(None, alias="status", description="Filter by status."),
    uow: UnitOfWork = Depends(get_uow),
) -> list[RelationshipRead]:
    return RelationshipService(uow).list(
        limit=page.limit, offset=page.offset, case_id=case_id, status=status_filter
    )


@router.post(
    "",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a relationship from approved observations",
)
def create_relationship(
    payload: RelationshipCreate,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> RelationshipRead:
    return RelationshipService(uow).create(payload, principal)


@router.get("/{relationship_id}", response_model=RelationshipRead, summary="Get a relationship")
def get_relationship(
    relationship_id: UUID, uow: UnitOfWork = Depends(get_uow)
) -> RelationshipRead:
    return RelationshipService(uow).get(relationship_id)
