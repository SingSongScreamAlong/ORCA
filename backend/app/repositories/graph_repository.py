"""Graph projection access.

The relationship graph in Neo4j is a derived projection of the authoritative
relational record. This module defines the projection interface plus two
implementations:

* ``InMemoryGraphRepository`` — a no-op used by the skeleton's default backend.
* ``Neo4jGraphRepository`` — the production target; mirrors entities and confirmed
  relationships into Neo4j.

PostgreSQL is authoritative. If the projection and the record ever disagree, the
record wins and the projection is rebuilt.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.models.enums import EntityType, RelationshipType


class GraphRepository(Protocol):
    """The operations the service layer needs from the graph projection."""

    def upsert_entity(self, entity_id: UUID, entity_type: EntityType, value: str) -> None: ...

    def upsert_relationship(
        self,
        relationship_id: UUID,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: RelationshipType,
        confidence: float,
    ) -> None: ...

    def neighbors(self, entity_id: UUID) -> list[UUID]: ...


class InMemoryGraphRepository:
    """No-op projection for the skeleton backend.

    Entities and relationships already live in the in-memory store; there is no
    separate graph to maintain. Methods are present so the service layer can call the
    projection unconditionally.
    """

    def upsert_entity(self, entity_id: UUID, entity_type: EntityType, value: str) -> None:
        return None

    def upsert_relationship(
        self,
        relationship_id: UUID,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: RelationshipType,
        confidence: float,
    ) -> None:
        return None

    def neighbors(self, entity_id: UUID) -> list[UUID]:
        return []


class Neo4jGraphRepository:
    """Neo4j-backed projection (production target).

    Implemented against the driver in ``app.core.graph``. Cypher is written so that
    re-running it is idempotent (``MERGE``), keeping the projection convergent with
    the relational record.
    """

    def __init__(self, driver) -> None:
        self._driver = driver

    def upsert_entity(self, entity_id: UUID, entity_type: EntityType, value: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MERGE (e:Entity {id: $id}) "
                "SET e.entity_type = $type, e.value = $value",
                id=str(entity_id), type=entity_type.value, value=value,
            )

    def upsert_relationship(
        self,
        relationship_id: UUID,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relationship_type: RelationshipType,
        confidence: float,
    ) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                "MERGE (a)-[r:RELATED {id: $rid}]->(b) "
                "SET r.relationship_type = $type, r.confidence = $confidence",
                src=str(source_entity_id), dst=str(target_entity_id),
                rid=str(relationship_id), type=relationship_type.value, confidence=confidence,
            )

    def neighbors(self, entity_id: UUID) -> list[UUID]:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (e:Entity {id: $id})-[:RELATED]-(n:Entity) RETURN n.id AS id",
                id=str(entity_id),
            )
            return [UUID(record["id"]) for record in result]
