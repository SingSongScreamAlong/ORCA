"""Report API schemas.

A report draft is generated from a case using only approved evidence.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import ReportStatus
from app.schemas.common import ORCAModel


class ReportRead(ORCAModel):
    id: UUID
    case_id: UUID
    title: str
    author: str
    status: ReportStatus
    body: str | None
    created_at: datetime
    updated_at: datetime
