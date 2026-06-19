"""Cluster service.

Clusters group existing entities and observations; they do not own them. The skeleton
exposes read access and a simple analyst-created cluster path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.security import Principal
from app.models.enums import ClusterStatus, Origin
from app.repositories.cluster_repository import ClusterRepository
from app.repositories.entity_repository import EntityRepository
from app.repositories.observation_repository import ObservationRepository
from app.schemas.cluster import ClusterCreate, ClusterRead
from app.services.errors import NotFoundError, ValidationError


class ClusterService:
    def __init__(self) -> None:
        self._clusters = ClusterRepository()
        self._entities = EntityRepository()
        self._observations = ObservationRepository()

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ClusterRead]:
        return self._clusters.list(limit=limit, offset=offset)

    def get(self, cluster_id) -> ClusterRead:
        cluster = self._clusters.get(cluster_id)
        if cluster is None:
            raise NotFoundError(f"Cluster {cluster_id} not found")
        return cluster

    def create(self, payload: ClusterCreate, principal: Principal) -> ClusterRead:
        for entity_id in payload.entity_ids:
            if self._entities.get(entity_id) is None:
                raise ValidationError(f"Entity {entity_id} does not exist")
        for observation_id in payload.observation_ids:
            if self._observations.get(observation_id) is None:
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
        return self._clusters.add(cluster)
