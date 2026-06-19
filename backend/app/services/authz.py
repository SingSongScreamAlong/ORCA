"""Shared authorization helpers for review/evidence decisions.

Separation of duties: a user may not approve their own proposed intelligence. An
administrator may bypass this with an explicit override, which is recorded as a
distinct audit event. Callers must already have required ``REVIEW_DECIDE``.
"""

from __future__ import annotations

from app.core.rbac import Capability, can
from app.core.security import Principal
from app.services.errors import PermissionDenied


def authorize_decision(principal: Principal, proposer_id: str | None, override: bool) -> bool:
    """Validate a decision. Returns True if it is an admin override.

    * ``override=True`` requires the ADMIN_OVERRIDE capability (admin only).
    * Without override, deciding on one's own proposal is forbidden (self-review).
    """
    if override:
        if not can(principal.role, Capability.ADMIN_OVERRIDE):
            raise PermissionDenied("Only an administrator may override the self-review control.")
        return True

    if proposer_id is not None and proposer_id == principal.id:
        raise PermissionDenied(
            "You cannot decide on your own proposed intelligence without an admin override."
        )
    return False
