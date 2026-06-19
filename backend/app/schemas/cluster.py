"""Cluster API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import ClusterStatus, Origin
from app.schemas.common import ConfidenceScore, ORCAModel


class ClusterCreate(ORCAModel):
    title: str = Field(min_length=1)
    confidence: ConfidenceScore = 0.0
    entity_ids: list[UUID] = Field(default_factory=list)
    observation_ids: list[UUID] = Field(default_factory=list)


class ClusterRead(ORCAModel):
    id: UUID
    title: str
    status: ClusterStatus
    confidence: float
    origin: Origin
    entity_ids: list[UUID]
    observation_ids: list[UUID]
    created_at: datetime
