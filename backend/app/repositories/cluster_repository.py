"""Cluster data access."""

from __future__ import annotations

from uuid import UUID

from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.cluster import ClusterRead


class ClusterRepository:
    def list(self, *, limit: int = 50, offset: int = 0) -> list[ClusterRead]:
        return paginate(newest_first(store.clusters.values()), limit=limit, offset=offset)

    def count(self) -> int:
        return len(store.clusters)

    def get(self, cluster_id: UUID) -> ClusterRead | None:
        return store.clusters.get(cluster_id)

    def add(self, cluster: ClusterRead) -> ClusterRead:
        store.clusters[cluster.id] = cluster
        return cluster
