"""Case timeline schemas.

The timeline shows approved observations and relationship changes in chronological
order. It never shows proposed or rejected observations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from app.schemas.common import ORCAModel


class TimelineEventKind(str, Enum):
    OBSERVATION_APPROVED = "observation_approved"
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_APPROVED = "relationship_approved"


class TimelineEvent(ORCAModel):
    timestamp: datetime
    kind: TimelineEventKind
    summary: str
    ref_type: str
    ref_id: UUID
