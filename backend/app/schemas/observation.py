"""Observation API schemas.

In v0.2 an observation enters the review queue with ``status = proposed`` and carries
optional case linkage, legal/handling metadata, and inline source metadata for intake.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import ReviewStatus
from app.schemas.common import ConfidenceScore, ORCAModel
from app.schemas.handling import Handling
from app.schemas.source import SourceCreate


class ObservationCreate(ORCAModel):
    case_id: UUID | None = Field(default=None, description="Case this observation is intaked into.")
    timestamp: datetime = Field(description="When the fact was observed (collector-supplied).")
    # Provide either an existing source_id or inline source metadata (exactly one).
    source_id: UUID | None = Field(default=None, description="An existing source.")
    source: SourceCreate | None = Field(default=None, description="Inline source metadata.")
    collector: str = Field(min_length=1, description="Analyst id or collector name.")
    location: str | None = None
    notes: str | None = None
    confidence: ConfidenceScore = 0.0
    entity_ids: list[UUID] = Field(default_factory=list, description="Entities referenced.")
    handling: Handling = Field(default_factory=Handling, description="Legal/handling metadata.")

    @model_validator(mode="after")
    def _exactly_one_source(self) -> ObservationCreate:
        if (self.source_id is None) == (self.source is None):
            raise ValueError("Provide exactly one of 'source_id' or 'source'.")
        return self


class ObservationRead(ORCAModel):
    id: UUID
    case_id: UUID | None
    timestamp: datetime
    source_id: UUID
    collector: str
    location: str | None
    notes: str | None
    confidence: float
    status: ReviewStatus
    entity_ids: list[UUID]
    handling: Handling
    decided_by: str | None
    decided_at: datetime | None
    created_at: datetime
