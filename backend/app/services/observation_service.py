"""Observation service.

Enforces: every observation references exactly one existing source; referenced
entities and evidence must exist; observations are append-only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.security import Principal
from app.repositories.entity_repository import EntityRepository
from app.repositories.observation_repository import ObservationRepository
from app.repositories.source_repository import EvidenceRepository, SourceRepository
from app.schemas.observation import ObservationCreate, ObservationRead
from app.services.errors import NotFoundError, ValidationError


class ObservationService:
    def __init__(self) -> None:
        self._observations = ObservationRepository()
        self._sources = SourceRepository()
        self._entities = EntityRepository()
        self._evidence = EvidenceRepository()

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ObservationRead]:
        return self._observations.list(limit=limit, offset=offset)

    def get(self, observation_id) -> ObservationRead:
        observation = self._observations.get(observation_id)
        if observation is None:
            raise NotFoundError(f"Observation {observation_id} not found")
        return observation

    def create(self, payload: ObservationCreate, principal: Principal) -> ObservationRead:
        # Invariant: an observation must reference exactly one existing source.
        if self._sources.get(payload.source_id) is None:
            raise ValidationError(f"Source {payload.source_id} does not exist")

        for entity_id in payload.entity_ids:
            if self._entities.get(entity_id) is None:
                raise ValidationError(f"Referenced entity {entity_id} does not exist")

        for evidence_id in payload.evidence_ids:
            if self._evidence.get(evidence_id) is None:
                raise ValidationError(f"Referenced evidence {evidence_id} does not exist")

        observation = ObservationRead(
            id=uuid4(),
            timestamp=payload.timestamp,
            source_id=payload.source_id,
            collector=payload.collector or principal.id,
            location=payload.location,
            notes=payload.notes,
            confidence=payload.confidence,
            entity_ids=list(payload.entity_ids),
            evidence_ids=list(payload.evidence_ids),
            created_at=datetime.now(UTC),
        )
        return self._observations.add(observation)
