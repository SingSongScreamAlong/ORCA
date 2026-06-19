"""Audit log ORM model — append-only record of consequential actions.

There is no update or delete path for audit entries by design. See ``docs/security.md``.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class AuditLogEntry(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "audit_log"

    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Free-string ``action`` keeps the log forward-compatible with new audited
    # operations without a schema change.
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
