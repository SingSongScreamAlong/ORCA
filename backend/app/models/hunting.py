"""Hunting Grounds ORM models — the source/NAI registry and the CSAM-escalation channel.

These make the Hunting Grounds registry and the report-only escalation channel **durable** (the
system of record), so proposals, authorizations, and the append-only per-record history survive a
restart rather than living only in the development store.

Each row keeps the few fields worth indexing for filtering (``status``, ``aor``) plus a JSONB
``document`` holding the full Pydantic read model — including the nested ``history``. Storing the
record as a document keeps the evolving registry schema from needing a migration per field, and
mirrors how the rest of the codebase persists sub-objects (handling, legal flags, manifests) as
JSONB. The escalation table stores **no media** — only the pointer/metadata the charter's hard-stop
permits.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class HuntingSourceRow(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "hunting_sources"

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    aor: Mapped[str] = mapped_column(String(255), nullable=False)
    document: Mapped[dict] = mapped_column(JSONB, nullable=False)


class HuntingEscalationRow(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "hunting_escalations"

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    aor: Mapped[str] = mapped_column(String(255), nullable=False)
    document: Mapped[dict] = mapped_column(JSONB, nullable=False)


class HuntingWatchlistRow(UUIDPrimaryKey, TimestampMixin, Base):
    """An operator-managed AOR the autonomous cadence sweeps. ``aor_key`` (lower-cased) is unique."""

    __tablename__ = "hunting_watchlist"

    aor_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    aor: Mapped[str] = mapped_column(String(255), nullable=False)
    added_by: Mapped[str] = mapped_column(String(255), nullable=False)
