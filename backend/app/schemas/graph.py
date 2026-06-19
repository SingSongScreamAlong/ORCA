"""Relationship graph / discovery API schemas (v0.5).

Graph views are computed from the authoritative record of **approved** relationships.
Only approved relationships and the entities they connect appear — proposed, rejected,
and needs-more-review relationships never leak into discovery.
"""

from __future__ import annotations

from uuid import UUID

from app.models.enums import EntityType, RelationshipType
from app.schemas.common import ORCAModel


class GraphNode(ORCAModel):
    id: UUID
    entity_type: EntityType
    value: str


class GraphEdge(ORCAModel):
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: RelationshipType
    confidence: float


class GraphView(ORCAModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathView(ORCAModel):
    found: bool
    length: int  # number of hops (edges)
    nodes: list[GraphNode]  # ordered from source to target
    edges: list[GraphEdge]  # ordered along the path
