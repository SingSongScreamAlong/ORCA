"""Entity service.

Enforces deduplication by ``(entity_type, value)``: creating an entity that already
exists returns the existing one rather than a duplicate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.security import Principal
from app.repositories.entity_repository import EntityRepository
from app.schemas.entity import EntityCreate, EntityRead
from app.services.errors import NotFoundError


class EntityService:
    def __init__(self) -> None:
        self._entities = EntityRepository()

    def list(self, *, limit: int = 50, offset: int = 0) -> list[EntityRead]:
        return self._entities.list(limit=limit, offset=offset)

    def get(self, entity_id) -> EntityRead:
        entity = self._entities.get(entity_id)
        if entity is None:
            raise NotFoundError(f"Entity {entity_id} not found")
        return entity

    def create(self, payload: EntityCreate, principal: Principal) -> EntityRead:
        # Deduplicate: the same value of the same type is one entity.
        existing = self._entities.find_by_value(payload.entity_type, payload.value)
        if existing is not None:
            return existing

        entity = EntityRead(
            id=uuid4(),
            entity_type=payload.entity_type,
            value=payload.value,
            confidence=payload.confidence,
            created_at=datetime.now(UTC),
        )
        return self._entities.add(entity)
