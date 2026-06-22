"""Hunting Grounds — source/NAI registry schemas (governance gate).

The registry is the executable form of ``docs/hunting_grounds_charter.md``: a source moves
``proposed → authorized → monitored`` (and ``suspended``/``retired``/``rejected``), and it can
**only** be authorized once a human records its lawful basis, access method, and jurisdiction.
Discovery (later) can only ever create ``proposed`` sources.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import (
    HuntingDiscoveryMethod,
    HuntingSourceCategory,
    HuntingSourceStatus,
)
from app.schemas.common import ORCAModel


class HuntingTransition(ORCAModel):
    """One immutable entry in a source's lifecycle history (append-only)."""

    from_status: HuntingSourceStatus | None
    to_status: HuntingSourceStatus
    by: str
    at: datetime
    note: str | None = None


class HuntingSourcePropose(ORCAModel):
    name: str = Field(min_length=1, description="Human label for the venue.")
    url: str = Field(min_length=1, description="Public host/URL of the venue.")
    category: HuntingSourceCategory = HuntingSourceCategory.OTHER
    aor: str = Field(min_length=1, description="Area of responsibility, e.g. 'Rhode Island'.")
    discovery_method: HuntingDiscoveryMethod = HuntingDiscoveryMethod.OPERATOR_SEED
    discovery_notes: str | None = None


class HuntingAuthorize(ORCAModel):
    """The authorization record. All three justification fields are required by the gate."""

    lawful_basis: str = Field(min_length=1, description="Why monitoring this source is lawful.")
    access_method: str = Field(min_length=1, description="How it will be accessed (e.g. licensed API).")
    jurisdiction: str = Field(min_length=1, description="Governing jurisdiction.")
    legal_review_note: str | None = Field(None, description="Legal reviewer's note / reference.")


class HuntingDecision(ORCAModel):
    """Reason for a reject / suspend / retire transition."""

    reason: str = Field(min_length=1)


class HuntingSourceRead(ORCAModel):
    id: UUID
    name: str
    url: str
    category: HuntingSourceCategory
    aor: str
    status: HuntingSourceStatus
    discovery_method: HuntingDiscoveryMethod
    discovery_notes: str | None
    proposed_by: str
    proposed_at: datetime
    # Authorization record (present once authorized):
    lawful_basis: str | None
    access_method: str | None
    jurisdiction: str | None
    legal_review_note: str | None
    authorized_by: str | None
    authorized_at: datetime | None
    last_decision_reason: str | None
    updated_at: datetime
    history: list[HuntingTransition]


class HuntingAorSummary(ORCAModel):
    """Rollup of the registry for one area of responsibility (or all)."""

    aor: str
    total: int
    monitored: int
    by_status: dict[str, int]  # status value -> count


class HuntingSummary(ORCAModel):
    aors: list[HuntingAorSummary]
    totals: HuntingAorSummary
