"""Evidence ORM model — a preserved, immutable artifact.

Integrity is anchored by ``sha256``. Evidence is write-once; there is no update path
for the bytes or the hash. See ``docs/security.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import EvidenceType
from app.models.types import pg_enum


class Evidence(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "evidence"

    evidence_type: Mapped[EvidenceType] = mapped_column(
        pg_enum(EvidenceType, "evidence_type"), nullable=False
    )
    # The integrity anchor: bytes are re-hashed on read and compared to this value.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
