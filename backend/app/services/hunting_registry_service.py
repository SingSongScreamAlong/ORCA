"""Hunting Grounds source/NAI registry service.

The executable enforcement of ``docs/hunting_grounds_charter.md``'s authorization-first
lifecycle:

    proposed ──authorize──▶ authorized ──start──▶ monitored
       │                        │  ▲                  │
       └──reject──▶ rejected    │  └──── resume ──────┤
                                └── suspend ◀─────────┘
    authorized/monitored/suspended ──retire──▶ retired

Invariants enforced here (not by convention):
* a source can be **authorized only from proposed**, and only with a complete authorization
  record (lawful basis + access method + jurisdiction);
* a source can be **monitored only after it was authorized** (never straight from proposed);
* every transition appends an immutable history entry (who/when/why).

Discovery jobs (a later milestone) call ``propose`` only — they can never authorize.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.security import Principal
from app.models.enums import HuntingSourceStatus
from app.repositories.store import store
from app.schemas.hunting import (
    HuntingAorSummary,
    HuntingAuthorize,
    HuntingSourcePropose,
    HuntingSourceRead,
    HuntingSummary,
    HuntingTransition,
)
from app.services.errors import NotFoundError, ValidationError

_S = HuntingSourceStatus


def _rollup(aor: str, group: list[HuntingSourceRead]) -> HuntingAorSummary:
    counts = {s.value: 0 for s in HuntingSourceStatus}
    for src in group:
        counts[src.status.value] += 1
    return HuntingAorSummary(
        aor=aor, total=len(group), monitored=counts[_S.MONITORED.value], by_status=counts
    )


class HuntingRegistryService:
    def list(
        self, *, status: HuntingSourceStatus | None = None, aor: str | None = None
    ) -> list[HuntingSourceRead]:
        items = list(store.hunting_sources.values())
        if status is not None:
            items = [s for s in items if s.status == status]
        if aor is not None:
            items = [s for s in items if s.aor.lower() == aor.lower()]
        return sorted(items, key=lambda s: s.proposed_at, reverse=True)

    def get(self, source_id: UUID) -> HuntingSourceRead:
        source = store.hunting_sources.get(source_id)
        if source is None:
            raise NotFoundError(f"Hunting source {source_id} not found")
        return source

    def summary(self) -> HuntingSummary:
        """An AOR rollup of the registry — the regional posture at a glance (read-only)."""
        items = list(store.hunting_sources.values())
        by_aor: dict[str, list[HuntingSourceRead]] = {}
        for src in items:
            by_aor.setdefault(src.aor, []).append(src)
        aors = [_rollup(aor, group) for aor, group in sorted(by_aor.items())]
        return HuntingSummary(aors=aors, totals=_rollup("All AORs", items))

    def propose(self, payload: HuntingSourcePropose, principal: Principal) -> HuntingSourceRead:
        now = datetime.now(UTC)
        first = HuntingTransition(
            from_status=None, to_status=_S.PROPOSED, by=principal.username, at=now
        )
        source = HuntingSourceRead(
            id=uuid4(),
            name=payload.name,
            url=payload.url,
            category=payload.category,
            aor=payload.aor,
            status=_S.PROPOSED,
            discovery_method=payload.discovery_method,
            discovery_notes=payload.discovery_notes,
            proposed_by=principal.username,
            proposed_at=now,
            lawful_basis=None,
            access_method=None,
            jurisdiction=None,
            legal_review_note=None,
            authorized_by=None,
            authorized_at=None,
            last_decision_reason=None,
            updated_at=now,
            history=[first],
        )
        store.hunting_sources[source.id] = source
        return source

    def authorize(
        self, source_id: UUID, payload: HuntingAuthorize, principal: Principal
    ) -> HuntingSourceRead:
        source = self.get(source_id)
        if source.status != _S.PROPOSED:
            raise ValidationError(
                f"Only a proposed source can be authorized (this one is '{source.status.value}')."
            )
        now = datetime.now(UTC)
        # The gate: an authorization record is mandatory (schema requires the fields non-empty).
        return self._transition(
            source,
            _S.AUTHORIZED,
            principal,
            note=payload.legal_review_note,
            patch={
                "lawful_basis": payload.lawful_basis,
                "access_method": payload.access_method,
                "jurisdiction": payload.jurisdiction,
                "legal_review_note": payload.legal_review_note,
                "authorized_by": principal.username,
                "authorized_at": now,
            },
        )

    def reject(self, source_id: UUID, reason: str, principal: Principal) -> HuntingSourceRead:
        source = self.get(source_id)
        if source.status != _S.PROPOSED:
            raise ValidationError("Only a proposed source can be rejected.")
        return self._transition(
            source, _S.REJECTED, principal, note=reason, patch={"last_decision_reason": reason}
        )

    def start_monitoring(self, source_id: UUID, principal: Principal) -> HuntingSourceRead:
        source = self.get(source_id)
        if source.status not in (_S.AUTHORIZED, _S.SUSPENDED):
            raise ValidationError(
                "A source must be authorized (or suspended) before it can be monitored — "
                f"this one is '{source.status.value}'."
            )
        return self._transition(source, _S.MONITORED, principal)

    def suspend(self, source_id: UUID, reason: str, principal: Principal) -> HuntingSourceRead:
        source = self.get(source_id)
        if source.status not in (_S.AUTHORIZED, _S.MONITORED):
            raise ValidationError("Only an authorized or monitored source can be suspended.")
        return self._transition(
            source, _S.SUSPENDED, principal, note=reason, patch={"last_decision_reason": reason}
        )

    def retire(self, source_id: UUID, reason: str, principal: Principal) -> HuntingSourceRead:
        source = self.get(source_id)
        if source.status in (_S.RETIRED, _S.REJECTED):
            raise ValidationError(f"Source is already '{source.status.value}'.")
        return self._transition(
            source, _S.RETIRED, principal, note=reason, patch={"last_decision_reason": reason}
        )

    # --- internal ----------------------------------------------------------------

    def _transition(
        self,
        source: HuntingSourceRead,
        to: HuntingSourceStatus,
        principal: Principal,
        *,
        note: str | None = None,
        patch: dict | None = None,
    ) -> HuntingSourceRead:
        now = datetime.now(UTC)
        entry = HuntingTransition(
            from_status=source.status, to_status=to, by=principal.username, at=now, note=note
        )
        updated = source.model_copy(
            update={
                "status": to,
                "updated_at": now,
                "history": [*source.history, entry],
                **(patch or {}),
            }
        )
        store.hunting_sources[updated.id] = updated
        return updated
