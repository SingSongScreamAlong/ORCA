"""Neo4j connection management — the relationship graph projection.

Neo4j stores entities as nodes and relationships as edges, mirroring the relational
record. PostgreSQL is authoritative; the graph is a derived, queryable projection.

In the skeleton this driver is created lazily and only when the PostgreSQL/Neo4j
backend is active. The graph repository (``app.repositories.graph_repository``)
provides both a Neo4j-backed and an in-memory implementation.
"""

from __future__ import annotations

from app.core.config import get_settings

_driver = None


def get_driver():
    """Return a cached Neo4j driver, creating it on first use.

    Imported lazily so the skeleton does not require the ``neo4j`` package or a
    running database when the in-memory backend is used.
    """
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase  # local import keeps it optional

        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
