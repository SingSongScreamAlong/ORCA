"""Relationship graph / discovery endpoints (v0.5).

Read-only views over approved relationships, guarded by READ_CASE_MATERIAL.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_uow, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.graph import GraphView, PathView
from app.services.graph_query_service import GraphQueryService

router = APIRouter(prefix="/graph", tags=["graph"])

_READ = Capability.READ_CASE_MATERIAL


@router.get("/neighbors/{entity_id}", response_model=GraphView, summary="An entity's neighbours")
def neighbors(
    entity_id: UUID,
    _: Principal = Depends(require(_READ)),
    uow: UnitOfWork = Depends(get_uow),
) -> GraphView:
    return GraphQueryService(uow).neighbors(entity_id)


@router.get("/path", response_model=PathView, summary="Shortest path between two entities")
def path(
    source: UUID = Query(..., description="Source entity id."),
    target: UUID = Query(..., description="Target entity id."),
    max_depth: int = Query(6, ge=1, le=12, description="Maximum hops to search."),
    _: Principal = Depends(require(_READ)),
    uow: UnitOfWork = Depends(get_uow),
) -> PathView:
    return GraphQueryService(uow).shortest_path(source, target, max_depth=max_depth)
