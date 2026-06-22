"""Hunting Grounds — operator-managed AOR watchlist.

The set of areas of responsibility the autonomous cadence sweeps for new venues, managed from the
UI instead of an environment variable — so an operator adds or removes a region without a redeploy.
The persisted watchlist takes precedence over the ``ORCA_HUNTING_DISCOVERY_AORS`` env fallback;
when it's empty, the env list is used (a convenient seed). Changes are audited.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import HuntingWatchlistEntry
from app.services.errors import ValidationError


class HuntingWatchlistService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(self) -> list[HuntingWatchlistEntry]:
        return self.uow.hunting_watchlist.list()

    def aors(self) -> list[str]:
        """The AOR strings on the watchlist (for the discovery sweep / cadence)."""
        return [e.aor for e in self.uow.hunting_watchlist.list()]

    def add(self, aor: str, principal: Principal) -> HuntingWatchlistEntry:
        aor = aor.strip()
        if not aor:
            raise ValidationError("An AOR is required.")
        entry = HuntingWatchlistEntry(aor=aor, added_by=principal.username, added_at=datetime.now(UTC))
        self.uow.hunting_watchlist.add(entry)
        self._audit(principal, "hunting.watchlist.added", aor)
        return entry

    def remove(self, aor: str, principal: Principal) -> None:
        self.uow.hunting_watchlist.remove(aor)
        self._audit(principal, "hunting.watchlist.removed", aor)

    def _audit(self, principal: Principal, action: str, aor: str) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type="hunting_watchlist",
                target_id=aor,
                case_id=None,
                context={"aor": aor},
            )
        )
