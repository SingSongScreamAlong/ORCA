"""PostgreSQL connection management — the system of record.

In the skeleton the default storage backend is in-memory, so the engine is created
lazily and only when ``ORCA_STORAGE_BACKEND=postgres``. The ORM models in
``app.models`` define the canonical relational schema regardless of backend.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
_SessionLocal: sessionmaker | None = None


def _init_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        return
    settings = get_settings()
    _engine = create_engine(settings.postgres_dsn, pool_pre_ping=True, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def new_session() -> Session:
    """Return a new database session (caller manages its lifecycle)."""
    _init_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session.

    Only used when the PostgreSQL backend is active.
    """
    session = new_session()
    try:
        yield session
    finally:
        session.close()
