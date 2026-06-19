"""Review queue API schemas.

A review item must always carry the rationale (why it was surfaced), the supporting
evidence, and a confidence. The decision endpoint records the analyst's action.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from app.models.enums import ReviewItemType, ReviewStatus
from app.schemas.common import ORCAModel


class ReviewItemRead(ORCAModel):
    id: UUID
    item_type: ReviewItemType
    subject_type: str
    subject_id: UUID
    case_id: UUID | None
    # Why this was surfaced — always present.
    rationale: str
    confidence: float
    evidence_ids: list[UUID]
    status: ReviewStatus
    decided_by: str | None
    decided_at: datetime | None
    created_at: datetime


class ReviewDecision(str, Enum):
    """The three analyst actions available on a review item."""

    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_MORE_REVIEW = "needs_more_review"


class ReviewDecisionRequest(ORCAModel):
    decision: ReviewDecision
    note: str | None = None
