"""Evidence Item API schemas (v0.3 — the Evidence Locker).

An Evidence Item is the rich, case-scoped, auditable record of a piece of evidence:
metadata, source attribution, an optional link to an observation, legal/handling flags,
and — when bytes are available — a SHA-256 integrity hash.

The locker is for metadata, lawful files, and partner-approved workflows only. It must
never hold material prohibited by docs/safety_and_handling.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.models.enums import EvidenceStatus, EvidenceType
from app.schemas.common import ORCAModel


class LegalFlags(ORCAModel):
    lawful_basis: str | None = None
    requires_legal_review: bool = False
    sensitive: bool = False
    partner_approved: bool = False


class EvidenceItemCreate(ORCAModel):
    case_id: UUID
    source_id: UUID
    observation_id: UUID | None = None
    title: str = Field(min_length=1)
    description: str | None = None
    evidence_type: EvidenceType
    # External reference when bytes are not stored in ORCA.
    storage_uri: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    # Partner-provided hash when bytes are not available to ORCA.
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    captured_at: datetime | None = None
    captured_by: str | None = None
    access_method: str = Field(
        default="manual_upload",
        description="How the item reached ORCA (e.g. manual_upload, partner_transfer, analyst_capture).",
    )
    legal_flags: LegalFlags = Field(default_factory=LegalFlags)
    handling_notes: str | None = None
    # Optional inline content for ORCA to hash and store. Exactly one of these, or none.
    content_text: str | None = Field(default=None, description="Text content to hash/store.")
    content_base64: str | None = Field(default=None, description="Base64 bytes to hash/store.")


class EvidenceItemRead(ORCAModel):
    id: UUID
    case_id: UUID
    source_id: UUID
    observation_id: UUID | None
    title: str
    description: str | None
    evidence_type: EvidenceType
    storage_uri: str | None
    original_filename: str | None
    mime_type: str | None
    size_bytes: int | None
    sha256: str | None
    captured_at: datetime | None
    captured_by: str | None
    access_method: str
    legal_flags: LegalFlags
    handling_notes: str | None
    status: EvidenceStatus
    has_bytes: bool  # whether ORCA holds the bytes (so the hash can be re-verified)
    created_by: str
    created_at: datetime


class EvidenceLinkRequest(ORCAModel):
    observation_id: UUID


class EvidenceDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_MORE_REVIEW = "needs_more_review"
    QUARANTINE = "quarantine"


class EvidenceDecisionRequest(ORCAModel):
    decision: EvidenceDecision
    note: str | None = None


class EvidenceVerifyResult(ORCAModel):
    evidence_id: UUID
    has_bytes: bool
    recorded_sha256: str | None
    computed_sha256: str | None
    verified: bool | None  # None when there are no stored bytes to verify against
    message: str
