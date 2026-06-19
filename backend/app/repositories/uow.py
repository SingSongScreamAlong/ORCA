"""Unit of Work — the seam between the service layer and storage.

A unit of work bundles every repository plus the graph projection, and owns the
transaction boundary (``commit`` / ``rollback`` / ``close``). Services depend only on
this surface, so the same domain logic runs against the in-memory development store or
PostgreSQL in production.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.config import get_settings


@runtime_checkable
class UnitOfWork(Protocol):
    sources: object
    evidence: object
    entities: object
    observations: object
    relationships: object
    clusters: object
    cases: object
    reports: object
    reviews: object
    audit: object
    graph: object
    content: object  # evidence content store (SHA-256 integrity layer)

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


class InMemoryUnitOfWork:
    """Unit of work over the in-memory development store.

    Mutations apply immediately to the process-wide store, so ``commit`` and
    ``rollback`` are no-ops. This backend is for development and fast tests.
    """

    def __init__(self) -> None:
        from app.repositories.graph_repository import InMemoryGraphRepository
        from app.repositories.memory import (
            MemoryAuditRepository,
            MemoryCaseRepository,
            MemoryClusterRepository,
            MemoryEntityRepository,
            MemoryEvidenceRepository,
            MemoryObservationRepository,
            MemoryRelationshipRepository,
            MemoryReportRepository,
            MemoryReviewRepository,
            MemorySourceRepository,
        )
        from app.repositories.store import store

        self.sources = MemorySourceRepository(store)
        self.evidence = MemoryEvidenceRepository(store)
        self.entities = MemoryEntityRepository(store)
        self.observations = MemoryObservationRepository(store)
        self.relationships = MemoryRelationshipRepository(store)
        self.clusters = MemoryClusterRepository(store)
        self.cases = MemoryCaseRepository(store)
        self.reports = MemoryReportRepository(store)
        self.reviews = MemoryReviewRepository(store)
        self.audit = MemoryAuditRepository(store)
        self.graph = InMemoryGraphRepository()
        from app.core.content_store import build_content_store

        self.content = build_content_store()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def build_unit_of_work() -> UnitOfWork:
    """Construct a unit of work for the active storage backend."""
    settings = get_settings()
    if settings.uses_database:
        # Imported lazily so the in-memory backend needs no database drivers.
        from app.repositories.sql import build_sql_unit_of_work

        return build_sql_unit_of_work()
    return InMemoryUnitOfWork()
