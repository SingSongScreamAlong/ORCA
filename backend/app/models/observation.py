"""Observation ORM model — the foundational object.

Observations are append-only: there is no update path. Corrections are new
observations that reference the prior one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import observation_entities, observation_evidence
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Observation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "observations"

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

    entities = relationship("Entity", secondary=observation_entities, backref="observations")
    evidence = relationship("Evidence", secondary=observation_evidence, backref="observations")
