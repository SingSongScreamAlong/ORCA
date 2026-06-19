"""Audit log ORM model — append-only record of consequential actions.

There is no update or delete path for audit entries by design. See ``docs/security.md``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class AuditLogEntry(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "audit_log"

    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Optional case scope so the log can be filtered per case.
    case_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # Free-string ``action`` keeps the log forward-compatible with new audited
    # operations without a schema change.
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
