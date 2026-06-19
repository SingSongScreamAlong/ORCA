"""Source and evidence read endpoints.

These support the frontend's evidence-first views. Evidence is read-only over the API:
it is immutable once preserved.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Pagination, get_uow, pagination
from app.repositories.uow import UnitOfWork
from app.schemas.evidence import EvidenceRead
from app.schemas.source import SourceRead

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceRead], summary="List sources")
def list_sources(
    page: Pagination = Depends(pagination), uow: UnitOfWork = Depends(get_uow)
) -> list[SourceRead]:
    return uow.sources.list(limit=page.limit, offset=page.offset)


@router.get("/sources/{source_id}", response_model=SourceRead, summary="Get a source")
def get_source(source_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> SourceRead:
    source = uow.sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source


@router.get("/evidence", response_model=list[EvidenceRead], summary="List evidence")
def list_evidence(
    page: Pagination = Depends(pagination), uow: UnitOfWork = Depends(get_uow)
) -> list[EvidenceRead]:
    return uow.evidence.list(limit=page.limit, offset=page.offset)


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead, summary="Get evidence metadata")
def get_evidence(evidence_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> EvidenceRead:
    evidence = uow.evidence.get(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")
    return evidence
