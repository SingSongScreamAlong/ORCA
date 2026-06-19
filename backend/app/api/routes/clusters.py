"""Cluster endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Pagination, current_principal, get_uow, pagination
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.cluster import ClusterCreate, ClusterRead
from app.services.cluster_service import ClusterService

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterRead], summary="List clusters")
def list_clusters(
    page: Pagination = Depends(pagination), uow: UnitOfWork = Depends(get_uow)
) -> list[ClusterRead]:
    return ClusterService(uow).list(limit=page.limit, offset=page.offset)


@router.post(
    "",
    response_model=ClusterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cluster",
)
def create_cluster(
    payload: ClusterCreate,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> ClusterRead:
    return ClusterService(uow).create(payload, principal)


@router.get("/{cluster_id}", response_model=ClusterRead, summary="Get a cluster")
def get_cluster(cluster_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> ClusterRead:
    return ClusterService(uow).get(cluster_id)
