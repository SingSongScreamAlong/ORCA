"""Relationship ORM model — an evidence-backed link between two entities.

Invariant: a relationship must reference at least one supporting observation. This is
enforced in the service layer and reflected by the association to ``observations``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import relationship_observations
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import Origin, RelationshipType, ReviewStatus
from app.models.types import pg_enum


class Relationship(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint(
            "source_entity_id <> target_entity_id",
            name="ck_relationship_distinct_endpoints",
        ),
    )

    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        pg_enum(RelationshipType, "relationship_type"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin: Mapped[Origin] = mapped_column(
        pg_enum(Origin, "origin"), nullable=False, default=Origin.SYSTEM_PROPOSED
    )
    status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"), nullable=False, default=ReviewStatus.PROPOSED
    )

    supporting_observations = relationship(
        "Observation", secondary=relationship_observations, backref="relationships"
    )
