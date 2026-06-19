"""Observation API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ConfidenceScore, ORCAModel


class ObservationCreate(ORCAModel):
    timestamp: datetime = Field(description="When the fact was observed (collector-supplied).")
    source_id: UUID = Field(description="The source this observation came from (required).")
    collector: str = Field(min_length=1, description="Analyst id or collector name.")
    location: str | None = None
    notes: str | None = None
    confidence: ConfidenceScore = 0.0
    entity_ids: list[UUID] = Field(default_factory=list, description="Entities referenced.")
    evidence_ids: list[UUID] = Field(default_factory=list, description="Supporting evidence.")


class ObservationRead(ORCAModel):
    id: UUID
    timestamp: datetime
    source_id: UUID
    collector: str
    location: str | None
    notes: str | None
    confidence: float
    entity_ids: list[UUID]
    evidence_ids: list[UUID]
    created_at: datetime
