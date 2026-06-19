"""Entity API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import ConfidenceBand, EntityType, band_for
from app.schemas.common import ConfidenceScore, ORCAModel


class EntityCreate(ORCAModel):
    entity_type: EntityType
    value: str = Field(min_length=1, description="Canonicalized value (e.g. E.164 for phones).")
    confidence: ConfidenceScore = 1.0


class EntityRead(ORCAModel):
    id: UUID
    entity_type: EntityType
    value: str
    confidence: float
    created_at: datetime

    @property
    def confidence_band(self) -> ConfidenceBand:
        return band_for(self.confidence)
