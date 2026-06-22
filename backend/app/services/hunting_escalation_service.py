"""Suspected-minor / CSAM escalation service — the charter's hard-stop, in code.

A **report-only, never-store** channel: raising an escalation records a minimal urgent flag
(no media, no copied content) and routes it to a reporting queue; a human files the NCMEC
CyberTipline report and records its reference here. ORCA flags and routes — it does not store
or transmit the material.

Lifecycle: ``open → reported → closed`` (or ``open → dismissed`` when found not to be CSAM).
Every transition is recorded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.security import Principal
from app.models.enums import HuntingEscalationStatus
from app.repositories.store import store
from app.schemas.hunting_escalation import (
    HuntingEscalationRaise,
    HuntingEscalationRead,
    HuntingEscalationTransition,
)
from app.services.errors import NotFoundError, ValidationError

_E = HuntingEscalationStatus


class HuntingEscalationService:
    def list(self, *, status: HuntingEscalationStatus | None = None) -> list[HuntingEscalationRead]:
        items = list(store.hunting_escalations.values())
        if status is not None:
            items = [e for e in items if e.status == status]
        return sorted(items, key=lambda e: e.raised_at, reverse=True)

    def get(self, escalation_id: UUID) -> HuntingEscalationRead:
        item = store.hunting_escalations.get(escalation_id)
        if item is None:
            raise NotFoundError(f"Escalation {escalation_id} not found")
        return item

    def raise_concern(
        self, payload: HuntingEscalationRaise, principal: Principal
    ) -> HuntingEscalationRead:
        now = datetime.now(UTC)
        escalation = HuntingEscalationRead(
            id=uuid4(),
            source_id=payload.source_id,
            url=payload.url,
            aor=payload.aor,
            concern=payload.concern,
            status=_E.OPEN,
            raised_by=principal.username,
            raised_at=now,
            ncmec_reference=None,
            reported_by=None,
            reported_at=None,
            resolution=None,
            updated_at=now,
            history=[
                HuntingEscalationTransition(
                    from_status=None, to_status=_E.OPEN, by=principal.username, at=now
                )
            ],
        )
        store.hunting_escalations[escalation.id] = escalation
        return escalation

    def report(
        self, escalation_id: UUID, ncmec_reference: str, principal: Principal
    ) -> HuntingEscalationRead:
        escalation = self.get(escalation_id)
        if escalation.status != _E.OPEN:
            raise ValidationError("Only an open escalation can be marked reported.")
        now = datetime.now(UTC)
        return self._transition(
            escalation,
            _E.REPORTED,
            principal,
            note=f"NCMEC reference {ncmec_reference}",
            patch={
                "ncmec_reference": ncmec_reference,
                "reported_by": principal.username,
                "reported_at": now,
            },
        )

    def close(self, escalation_id: UUID, resolution: str, principal: Principal) -> HuntingEscalationRead:
        escalation = self.get(escalation_id)
        if escalation.status != _E.REPORTED:
            raise ValidationError("Only a reported escalation can be closed.")
        return self._transition(
            escalation, _E.CLOSED, principal, note=resolution, patch={"resolution": resolution}
        )

    def dismiss(self, escalation_id: UUID, reason: str, principal: Principal) -> HuntingEscalationRead:
        escalation = self.get(escalation_id)
        if escalation.status != _E.OPEN:
            raise ValidationError("Only an open escalation can be dismissed.")
        return self._transition(
            escalation, _E.DISMISSED, principal, note=reason, patch={"resolution": reason}
        )

    # --- internal ----------------------------------------------------------------

    def _transition(
        self,
        escalation: HuntingEscalationRead,
        to: HuntingEscalationStatus,
        principal: Principal,
        *,
        note: str | None = None,
        patch: dict | None = None,
    ) -> HuntingEscalationRead:
        now = datetime.now(UTC)
        entry = HuntingEscalationTransition(
            from_status=escalation.status, to_status=to, by=principal.username, at=now, note=note
        )
        updated = escalation.model_copy(
            update={
                "status": to,
                "updated_at": now,
                "history": [*escalation.history, entry],
                **(patch or {}),
            }
        )
        store.hunting_escalations[updated.id] = updated
        return updated
