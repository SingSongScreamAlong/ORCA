"""Evidence Item ORM model — the Evidence Locker (v0.3).

A case-scoped, auditable record of a piece of evidence: metadata, source attribution,
an optional link to an observation, legal/handling flags, and a SHA-256 integrity hash
when bytes are available. Bytes themselves (when present) live in the content store; the
``sha256`` here is the integrity anchor. See ``docs/security.md`` and
``docs/safety_and_handling.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import EvidenceStatus, EvidenceType
from app.models.types import pg_enum


class EvidenceItem(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "evidence_items"

    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("observations.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        pg_enum(EvidenceType, "evidence_type"), nullable=False
    )
    storage_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # The integrity anchor: re-hash the bytes and compare on verify.
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Whether ORCA holds the bytes (so the hash can be re-verified).
    has_bytes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_method: Mapped[str] = mapped_column(String(64), nullable=False, default="manual_upload")
    legal_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    handling_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EvidenceStatus] = mapped_column(
        pg_enum(EvidenceStatus, "evidence_status"), nullable=False, default=EvidenceStatus.PROPOSED
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
