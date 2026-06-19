"""Audit log API schemas (read-only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORCAModel


class AuditEntryRead(ORCAModel):
    id: UUID
    actor_id: str
    action: str
    target_type: str
    target_id: str
    case_id: UUID | None
    context: dict
    created_at: datetime
