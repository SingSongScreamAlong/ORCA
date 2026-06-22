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
from urllib.parse import urlparse
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import HuntingDiscoveryMethod, HuntingSourceStatus
from app.repositories.store import store
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    HuntingAorSummary,
    HuntingAuthorize,
    HuntingDiscoveryResult,
    HuntingDiscoveryRun,
    HuntingSourcePropose,
    HuntingSourceRead,
    HuntingSummary,
    HuntingTransition,
)
from app.services.errors import NotFoundError, ValidationError

_S = HuntingSourceStatus


def normalize_url(url: str) -> str:
    """A canonical key for de-duplication.

    Autonomous discovery re-runs hit the same venues repeatedly with trivially different URLs
    (scheme case, a trailing slash, a ``#fragment``, ``www.``). Normalizing the *comparison key*
    — while the source keeps its original, clickable URL — keeps repeated sweeps idempotent and
    the registry free of near-duplicate proposals. Query strings are preserved (they can be
    semantically meaningful for a listing); only incidental differences are collapsed.
    """
    raw = url.strip()
    parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="https")
    host = (parsed.hostname or "").lower()
    if not host:
        # Not URL-shaped — fall back to a lightly-normalized literal.
        return raw.rstrip("/").lower()
    if host.startswith("www."):
        host = host[4:]
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{host}{port}{path}{query}"


def _rollup(aor: str, group: list[HuntingSourceRead]) -> HuntingAorSummary:
    counts = {s.value: 0 for s in HuntingSourceStatus}
    for src in group:
        counts[src.status.value] += 1
    return HuntingAorSummary(
        aor=aor, total=len(group), monitored=counts[_S.MONITORED.value], by_status=counts
    )


class HuntingRegistryService:
    def __init__(self, uow: UnitOfWork | None = None) -> None:
        # When constructed with a unit of work (mutating routes), privileged actions are
        # written to ORCA's append-only audit log in addition to the per-source history.
        self.uow = uow

    def _audit(self, principal: Principal, action: str, source: HuntingSourceRead) -> None:
        if self.uow is None:
            return
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type="hunting_source",
                target_id=source.id,
                case_id=None,
                context={"name": source.name, "aor": source.aor, "status": source.status.value},
            )
        )

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

    def run_discovery(self, run: HuntingDiscoveryRun, principal: Principal) -> HuntingDiscoveryResult:
        """Propose discovered candidate venues into the registry as ``proposed`` (deduped by URL).

        This is the seam a future collector plugs into — "the hunt" surfaces *new* sites so the
        operator need not trawl. It can **only propose**; an administrator still authorizes each
        before anything is monitored. Re-running is idempotent: existing venues are skipped,
        compared by a normalized URL key so trivial variants (trailing slash, ``www.``, scheme
        case) don't slip through as duplicates.
        """
        existing = {normalize_url(s.url) for s in store.hunting_sources.values()}
        proposed = []
        skipped = 0
        for candidate in run.candidates:
            key = normalize_url(candidate.url)
            if key in existing:
                skipped += 1
                continue
            existing.add(key)
            proposed.append(
                self.propose(
                    HuntingSourcePropose(
                        name=candidate.name,
                        url=candidate.url,
                        category=candidate.category,
                        aor=run.aor,
                        discovery_method=HuntingDiscoveryMethod.DISCOVERY_JOB,
                        discovery_notes=candidate.notes,
                    ),
                    principal,
                )
            )
        return HuntingDiscoveryResult(aor=run.aor, proposed=proposed, skipped_existing=skipped)

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
        self._audit(principal, "hunting.source.proposed", source)
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
        self._audit(principal, f"hunting.source.{to.value}", updated)
        return updated
