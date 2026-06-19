"""Authentication scaffolding.

The skeleton does not implement a full identity provider. It models an authenticated
principal and a development default so the API can run and so authorization checks in
the service layer have an actor to record against. Real authentication (short-lived
tokens, an identity provider) is Phase 1 work — see ``docs/roadmap.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.rbac import Role


@dataclass(frozen=True)
class Principal:
    """An authenticated actor. ``id`` is recorded in the audit log."""

    id: str
    display_name: str
    role: Role


# Development principal used until authentication is implemented. Every audited action
# is attributed to a real principal; this placeholder makes that attribution explicit
# rather than anonymous.
DEV_PRINCIPAL = Principal(id="dev-analyst", display_name="Development Analyst", role=Role.REVIEWER)


def get_current_principal() -> Principal:
    """Return the current principal.

    Replaced by real token verification in Phase 1.
    """
    return DEV_PRINCIPAL
