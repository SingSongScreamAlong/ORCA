"""Graph repository selection.

Returns the graph projection implementation appropriate for the active storage
backend: a no-op for the in-memory skeleton, Neo4j when the database backend is on.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.repositories.graph_repository import (
    GraphRepository,
    InMemoryGraphRepository,
    Neo4jGraphRepository,
)


def get_graph_repository() -> GraphRepository:
    settings = get_settings()
    if settings.uses_database:
        from app.core.graph import get_driver

        return Neo4jGraphRepository(get_driver())
    return InMemoryGraphRepository()
