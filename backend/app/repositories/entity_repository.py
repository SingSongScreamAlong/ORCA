"""Entity data access, including deduplication by (entity_type, value)."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import EntityType
from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.entity import EntityRead


class EntityRepository:
    def list(self, *, limit: int = 50, offset: int = 0) -> list[EntityRead]:
        return paginate(newest_first(store.entities.values()), limit=limit, offset=offset)

    def count(self) -> int:
        return len(store.entities)

    def get(self, entity_id: UUID) -> EntityRead | None:
        return store.entities.get(entity_id)

    def find_by_value(self, entity_type: EntityType, value: str) -> EntityRead | None:
        """Return an existing entity with the same type and canonical value, if any."""
        for entity in store.entities.values():
            if entity.entity_type == entity_type and entity.value == value:
                return entity
        return None

    def add(self, entity: EntityRead) -> EntityRead:
        store.entities[entity.id] = entity
        return entity
