"""Cluster service.

Clusters group existing entities and observations; they do not own them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.security import Principal
from app.models.enums import ClusterStatus, Origin
from app.repositories.uow import UnitOfWork
from app.schemas.cluster import ClusterCreate, ClusterRead
from app.services.errors import NotFoundError, ValidationError


class ClusterService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ClusterRead]:
        return self.uow.clusters.list(limit=limit, offset=offset)

    def get(self, cluster_id: UUID) -> ClusterRead:
        cluster = self.uow.clusters.get(cluster_id)
        if cluster is None:
            raise NotFoundError(f"Cluster {cluster_id} not found")
        return cluster

    def create(self, payload: ClusterCreate, principal: Principal) -> ClusterRead:
        for entity_id in payload.entity_ids:
            if self.uow.entities.get(entity_id) is None:
                raise ValidationError(f"Entity {entity_id} does not exist")
        for observation_id in payload.observation_ids:
            if self.uow.observations.get(observation_id) is None:
                raise ValidationError(f"Observation {observation_id} does not exist")

        cluster = ClusterRead(
            id=uuid4(),
            title=payload.title,
            status=ClusterStatus.ACTIVE,
            confidence=payload.confidence,
            origin=Origin.ANALYST_CREATED,
            entity_ids=list(payload.entity_ids),
            observation_ids=list(payload.observation_ids),
            created_at=datetime.now(UTC),
        )
        return self.uow.clusters.add(cluster)
