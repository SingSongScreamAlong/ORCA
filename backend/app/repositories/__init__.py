"""Data access layer.

Repositories isolate storage details from the service layer. The skeleton ships an
in-memory implementation (``store.py``) seeded with a small, coherent example so the
API runs without a database. The PostgreSQL/Neo4j-backed implementations are the
production target (see ``app.core.database`` and ``app.core.graph``).
"""
