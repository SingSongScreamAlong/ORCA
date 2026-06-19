"""Evidence API schemas.

Evidence is immutable; there is no update schema. ``sha256`` is the integrity anchor.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import EvidenceType
from app.schemas.common import ORCAModel


class EvidenceRead(ORCAModel):
    id: UUID
    evidence_type: EvidenceType
    sha256: str
    storage_uri: str
    content_type: str | None
    captured_at: datetime
    source_id: UUID | None
    description: str | None
    created_at: datetime
