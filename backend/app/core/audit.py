"""Audit domain object.

Every consequential action — intake, approve/reject/needs_more_review, relationship
creation, report generation — is recorded as an append-only ``AuditEntry``. Storage is
provided by the audit repository on the active unit of work (in-memory or PostgreSQL);
there is no update or delete path by design. See ``docs/security.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AuditEntry:
    id: UUID
    actor_id: str
    action: str
    target_type: str
    target_id: str
    case_id: UUID | None
    context: dict
    created_at: datetime


def new_audit_entry(
    *,
    actor_id: str,
    action: str,
    target_type: str,
    target_id,
    case_id: UUID | None = None,
    context: dict | None = None,
) -> AuditEntry:
    """Construct an audit entry with system-set id and timestamp."""
    return AuditEntry(
        id=uuid4(),
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        case_id=case_id,
        context=context or {},
        created_at=datetime.now(UTC),
    )
