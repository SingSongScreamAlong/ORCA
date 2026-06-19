"""Authentication.

v0.4 introduces real, system-enforced identities. For local/dev use, the caller selects
a seeded user with the ``X-ORCA-User`` header (the frontend's dev user switcher sets it);
when absent, the configured default user is assumed. Production replaces ``resolve_principal``
with verification of a real credential (e.g. OIDC / short-lived tokens) — the rest of the
authorization stack (roles, capabilities, route guards, audit) is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import get_settings
from app.core.rbac import Role


class AuthenticationError(Exception):
    """Raised when an identity cannot be established (mapped to HTTP 401)."""


@dataclass(frozen=True)
class Principal:
    """An authenticated actor. ``id`` (the user id) is recorded in the audit log."""

    id: str
    username: str
    display_name: str
    role: Role


def resolve_principal(username: str | None, uow) -> Principal:
    """Resolve the acting principal from the supplied username (or the dev default)."""
    settings = get_settings()
    name = (username or settings.dev_default_user).strip()
    user = uow.users.get_by_username(name)
    if user is None:
        raise AuthenticationError(f"Unknown user '{name}'. Supply a valid X-ORCA-User header.")
    return Principal(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


def principal_user_id(principal: Principal) -> UUID:
    return UUID(principal.id)
