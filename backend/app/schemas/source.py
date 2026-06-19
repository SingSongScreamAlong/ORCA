"""Source API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import SourceReliability, SourceType
from app.schemas.common import ORCAModel


class SourceCreate(ORCAModel):
    source_type: SourceType
    name: str = Field(min_length=1)
    identifier: str | None = None
    reliability: SourceReliability = SourceReliability.UNKNOWN
    description: str | None = None


class SourceRead(ORCAModel):
    id: UUID
    source_type: SourceType
    name: str
    identifier: str | None
    reliability: SourceReliability
    description: str | None
    created_at: datetime
