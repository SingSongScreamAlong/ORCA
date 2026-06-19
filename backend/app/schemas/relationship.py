"""Relationship API schemas.

A relationship must reference at least one supporting observation — enforced both here
(``min_length=1``) and in the service layer.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import Origin, RelationshipType, ReviewStatus
from app.schemas.common import ConfidenceScore, ORCAModel


class RelationshipCreate(ORCAModel):
    case_id: UUID | None = None
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: RelationshipType
    confidence: ConfidenceScore = 0.0
    observation_ids: list[UUID] = Field(
        min_length=1,
        description="Supporting observations. At least one is required, and each must be approved.",
    )


class RelationshipRead(ORCAModel):
    id: UUID
    case_id: UUID | None
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: RelationshipType
    confidence: float
    origin: Origin
    status: ReviewStatus
    observation_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
