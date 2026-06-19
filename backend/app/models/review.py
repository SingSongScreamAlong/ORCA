"""ReviewItem ORM model — an item awaiting analyst decision in the review queue.

Each item records WHY it was surfaced (``rationale``), what supports it
(``evidence_ids`` / the referenced subject), its confidence, and its decision state.
The review queue is the place where "AI proposes, analysts decide" is enforced.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import ReviewItemType, ReviewStatus
from app.models.types import pg_enum


class ReviewItem(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "review_items"

    item_type: Mapped[ReviewItemType] = mapped_column(
        pg_enum(ReviewItemType, "review_item_type"), nullable=False
    )
    # The object this item is about (e.g. a relationship id).
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    # Human-readable explanation of why this was surfaced. Required — no item without it.
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=False, default=list
    )
    status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"), nullable=False, default=ReviewStatus.PROPOSED
    )
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
