"""Entity endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Pagination, current_principal, get_uow, pagination
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.entity import EntityCreate, EntityRead
from app.services.entity_service import EntityService

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("", response_model=list[EntityRead], summary="List entities")
def list_entities(
    page: Pagination = Depends(pagination), uow: UnitOfWork = Depends(get_uow)
) -> list[EntityRead]:
    return EntityService(uow).list(limit=page.limit, offset=page.offset)


@router.post(
    "",
    response_model=EntityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or resolve an entity",
)
def create_entity(
    payload: EntityCreate,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> EntityRead:
    return EntityService(uow).create(payload, principal)


@router.get("/{entity_id}", response_model=EntityRead, summary="Get an entity")
def get_entity(entity_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> EntityRead:
    return EntityService(uow).get(entity_id)
