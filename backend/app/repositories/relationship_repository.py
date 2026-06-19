"""Relationship data access."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import ReviewStatus
from app.repositories.base import newest_first, paginate
from app.repositories.store import store
from app.schemas.relationship import RelationshipRead


class RelationshipRepository:
    def list(
        self, *, limit: int = 50, offset: int = 0, status: ReviewStatus | None = None
    ) -> list[RelationshipRead]:
        values = store.relationships.values()
        if status is not None:
            values = [r for r in values if r.status == status]
        return paginate(newest_first(values), limit=limit, offset=offset)

    def count(self) -> int:
        return len(store.relationships)

    def get(self, relationship_id: UUID) -> RelationshipRead | None:
        return store.relationships.get(relationship_id)

    def add(self, relationship: RelationshipRead) -> RelationshipRead:
        store.relationships[relationship.id] = relationship
        return relationship

    def replace(self, relationship: RelationshipRead) -> RelationshipRead:
        """Replace a relationship record (e.g. after a status transition)."""
        store.relationships[relationship.id] = relationship
        return relationship
