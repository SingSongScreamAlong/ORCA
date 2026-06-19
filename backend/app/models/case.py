"""Case ORM model — an analyst work product; a VIEW over evidence.

A case references observations, entities, and clusters. It does not own them: deleting
a case removes the references (rows in the association tables) but never the referenced
objects. See ``docs/ontology_v0.1.md`` invariant 5.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import case_clusters, case_entities, case_observations
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import CaseStatus
from app.models.types import pg_enum


class Case(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "cases"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(
        pg_enum(CaseStatus, "case_status"), nullable=False, default=CaseStatus.OPEN
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Placeholder case-level legal/handling note (see docs/safety_and_handling.md).
    legal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    observations = relationship("Observation", secondary=case_observations)
    entities = relationship("Entity", secondary=case_entities)
    clusters = relationship("Cluster", secondary=case_clusters)
    reports = relationship("Report", back_populates="case", cascade="all, delete-orphan")
