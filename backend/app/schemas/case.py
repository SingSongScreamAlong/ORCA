"""Case API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import CaseStatus
from app.schemas.common import ORCAModel


class CaseCreate(ORCAModel):
    title: str = Field(min_length=1)
    owner: str = Field(min_length=1, description="Analyst responsible for the case.")
    summary: str | None = None
    # Placeholder legal/handling note for the case as a whole.
    legal_notes: str | None = None


class CaseRead(ORCAModel):
    id: UUID
    title: str
    status: CaseStatus
    owner: str
    summary: str | None
    legal_notes: str | None
    created_at: datetime
    updated_at: datetime


class CaseCounts(ORCAModel):
    observations_total: int
    observations_approved: int
    observations_pending: int
    relationships: int


class CaseDetail(ORCAModel):
    """A case plus aggregate counts for the overview tab."""

    case: CaseRead
    counts: CaseCounts
