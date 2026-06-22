"""Suspected-minor / CSAM escalation — a report-only, never-store channel.

This implements the charter's **CSAM hard-stop** (``docs/hunting_grounds_charter.md``). When an
operator suspects a listing depicts a minor or constitutes CSAM, they raise an **escalation**:
a minimal, urgent flag that routes to a reporting queue and tracks a manual **NCMEC
CyberTipline** filing. **The material is never stored.** The ``concern`` field is a short
description of *why* it was flagged — operators are instructed not to paste illegal content
into it; it is a pointer for the human filer, not a copy.

ORCA is a referral source: it flags and routes; a human files with NCMEC; ORCA does not
possess or transmit the material.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import HuntingEscalationStatus
from app.schemas.common import ORCAModel


class HuntingEscalationTransition(ORCAModel):
    from_status: HuntingEscalationStatus | None
    to_status: HuntingEscalationStatus
    by: str
    at: datetime
    note: str | None = None


class HuntingEscalationRaise(ORCAModel):
    source_id: UUID | None = Field(default=None, description="Related monitored source, if any.")
    url: str | None = Field(default=None, description="Where it was seen (a pointer, not content).")
    aor: str = Field(min_length=1)
    concern: str = Field(
        min_length=1,
        description="Why it was flagged. Do NOT include illegal content — this is a pointer "
        "for the human filer, never a copy of the material.",
    )


class HuntingEscalationReport(ORCAModel):
    ncmec_reference: str = Field(min_length=1, description="NCMEC CyberTipline report reference.")


class HuntingEscalationDecision(ORCAModel):
    reason: str = Field(min_length=1)


class HuntingEscalationRead(ORCAModel):
    id: UUID
    source_id: UUID | None
    url: str | None
    aor: str
    concern: str
    status: HuntingEscalationStatus
    raised_by: str
    raised_at: datetime
    ncmec_reference: str | None
    reported_by: str | None
    reported_at: datetime | None
    resolution: str | None
    updated_at: datetime
    history: list[HuntingEscalationTransition]
