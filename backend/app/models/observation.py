"""Observation ORM model — the foundational object.

Observations are append-only for their factual content. The only mutation is the
review lifecycle (``status`` / ``decided_by`` / ``decided_at``); corrections are new
observations that reference the prior one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import observation_entities
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import ReviewStatus
from app.models.types import pg_enum


class Observation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "observations"

    # Case this observation was intaked into (optional — a case is a view, not an owner).
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True
    )
    # Observed time, supplied by the collector (distinct from created_at).
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Every observation must reference exactly one source (ontology invariant).
    source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    collector: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Review lifecycle.
    status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"), nullable=False, default=ReviewStatus.PROPOSED
    )
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Legal/handling placeholder metadata (see docs/safety_and_handling.md).
    handling: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    entities = relationship("Entity", secondary=observation_entities, backref="observations")
    # Evidence links to an observation via EvidenceItem.observation_id (one-to-many).
    evidence_items = relationship("EvidenceItem", backref="observation")
