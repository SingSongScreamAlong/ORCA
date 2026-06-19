"""Append-only audit log.

Every consequential action — confirming, rejecting, or flagging a review item;
creating or deleting a case or report; a failed integrity check; role changes — is
recorded here. The log is append-only: there is no API to edit or delete entries.

The skeleton keeps entries in memory. The production target is an append-only table
in PostgreSQL (see ``app.models.audit`` and the migration).
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
    context: dict
    created_at: datetime


class AuditLog:
    """In-memory append-only audit log for the skeleton."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(
        self,
        *,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        context: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=uuid4(),
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            context=context or {},
            created_at=datetime.now(UTC),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        """Return all entries in insertion order (read-only view)."""
        return list(self._entries)


# Process-wide audit log instance for the in-memory skeleton.
audit_log = AuditLog()
