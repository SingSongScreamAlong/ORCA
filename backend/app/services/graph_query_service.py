"""Relationship graph queries (v0.5 — discovery).

Computes neighbourhoods, case subgraphs, and shortest paths over the authoritative
record of **approved** relationships. (The Neo4j projection, when enabled, mirrors the
same edges for scale; these queries read the relational record so they are correct and
testable on any backend.)
"""

from __future__ import annotations

from collections import deque
from uuid import UUID

from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.graph import GraphEdge, GraphNode, GraphView, PathView
from app.schemas.relationship import RelationshipRead
from app.services.case_access import CaseAccessService
from app.services.errors import NotFoundError


class GraphQueryService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    # --- helpers -----------------------------------------------------------------

    def _approved(
        self, case_id: UUID | None = None, accessible: set[UUID] | None = None
    ) -> list[RelationshipRead]:
        rels = self.uow.relationships.list(
            limit=100_000, status=ReviewStatus.APPROVED, case_id=case_id
        )
        if accessible is None:  # administrator, or unscoped internal call
            return rels
        # Discovery only traverses edges in cases the caller may read.
        return [r for r in rels if r.case_id in accessible]

    def _accessible(self, principal: Principal | None) -> set[UUID] | None:
        """Readable case ids for ``principal`` (``None`` = all / unscoped)."""
        if principal is None:
            return None
        return CaseAccessService(self.uow).readable_case_ids(principal)

    def _node(self, entity_id: UUID) -> GraphNode | None:
        entity = self.uow.entities.get(entity_id)
        if entity is None:
            return None
        return GraphNode(id=entity.id, entity_type=entity.entity_type, value=entity.value)

    @staticmethod
    def _edge(rel: RelationshipRead) -> GraphEdge:
        return GraphEdge(
            id=rel.id,
            source_entity_id=rel.source_entity_id,
            target_entity_id=rel.target_entity_id,
            relationship_type=rel.relationship_type,
            confidence=rel.confidence,
        )

    def _view(self, relationships: list[RelationshipRead]) -> GraphView:
        node_ids: set[UUID] = set()
        edges: list[GraphEdge] = []
        for rel in relationships:
            node_ids.add(rel.source_entity_id)
            node_ids.add(rel.target_entity_id)
            edges.append(self._edge(rel))
        nodes = [n for nid in node_ids if (n := self._node(nid)) is not None]
        return GraphView(nodes=nodes, edges=edges)

    # --- queries -----------------------------------------------------------------

    def neighbors(self, entity_id: UUID, principal: Principal | None = None) -> GraphView:
        if self.uow.entities.get(entity_id) is None:
            raise NotFoundError(f"Entity {entity_id} not found")
        accessible = self._accessible(principal)
        connected = [
            rel
            for rel in self._approved(accessible=accessible)
            if entity_id in (rel.source_entity_id, rel.target_entity_id)
        ]
        return self._view(connected)

    def case_subgraph(self, case_id: UUID) -> GraphView:
        if self.uow.cases.get(case_id) is None:
            raise NotFoundError(f"Case {case_id} not found")
        return self._view(self._approved(case_id=case_id))

    def shortest_path(
        self, source: UUID, target: UUID, max_depth: int = 6, principal: Principal | None = None
    ) -> PathView:
        for entity_id in (source, target):
            if self.uow.entities.get(entity_id) is None:
                raise NotFoundError(f"Entity {entity_id} not found")

        if source == target:
            node = self._node(source)
            return PathView(found=True, length=0, nodes=[node] if node else [], edges=[])

        accessible = self._accessible(principal)
        # Build an undirected adjacency over approved relationships.
        adjacency: dict[UUID, list[tuple[UUID, RelationshipRead]]] = {}
        for rel in self._approved(accessible=accessible):
            adjacency.setdefault(rel.source_entity_id, []).append((rel.target_entity_id, rel))
            adjacency.setdefault(rel.target_entity_id, []).append((rel.source_entity_id, rel))

        # BFS, tracking the edge used to reach each node.
        parents: dict[UUID, tuple[UUID, RelationshipRead]] = {}
        visited: set[UUID] = {source}
        queue: deque[tuple[UUID, int]] = deque([(source, 0)])
        found = False
        while queue:
            current, depth = queue.popleft()
            if current == target:
                found = True
                break
            if depth >= max_depth:
                continue
            for neighbor, rel in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parents[neighbor] = (current, rel)
                    queue.append((neighbor, depth + 1))

        if not found:
            return PathView(found=False, length=0, nodes=[], edges=[])

        # Reconstruct the path from target back to source.
        node_chain: list[UUID] = [target]
        edge_chain: list[GraphEdge] = []
        cursor = target
        while cursor != source:
            prev, rel = parents[cursor]
            edge_chain.append(self._edge(rel))
            node_chain.append(prev)
            cursor = prev
        node_chain.reverse()
        edge_chain.reverse()
        nodes = [n for nid in node_chain if (n := self._node(nid)) is not None]
        return PathView(found=True, length=len(edge_chain), nodes=nodes, edges=edge_chain)
