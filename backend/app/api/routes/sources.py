"""Source read endpoints.

These support the frontend's evidence-first views. (Evidence items live under the
``/evidence`` router — see ``routes/evidence.py``.)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Pagination, get_uow, pagination, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.source import SourceRead

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceRead], summary="List sources")
def list_sources(
    page: Pagination = Depends(pagination),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[SourceRead]:
    return uow.sources.list(limit=page.limit, offset=page.offset)


@router.get("/sources/{source_id}", response_model=SourceRead, summary="Get a source")
def get_source(
    source_id: UUID,
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> SourceRead:
    source = uow.sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source
