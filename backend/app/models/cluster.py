"""Cluster ORM model — a grouping of related entities and observations."""

from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import cluster_entities, cluster_observations
from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import ClusterStatus, Origin
from app.models.types import pg_enum


class Cluster(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "clusters"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[ClusterStatus] = mapped_column(
        pg_enum(ClusterStatus, "cluster_status"), nullable=False, default=ClusterStatus.PROPOSED
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    origin: Mapped[Origin] = mapped_column(
        pg_enum(Origin, "origin"), nullable=False, default=Origin.SYSTEM_PROPOSED
    )

    entities = relationship("Entity", secondary=cluster_entities, backref="clusters")
    observations = relationship("Observation", secondary=cluster_observations, backref="clusters")
