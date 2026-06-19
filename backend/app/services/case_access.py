"""Per-case authorization (v0.6 — Case Membership & Authorization Scoping).

RBAC (``app.core.rbac``) answers *what kind of user are you?*. This module answers
*which case are you allowed to access, and how?*. A non-admin must hold an **active**
membership in a case to see or act on it; the membership's case role decides what they
may do there. Administrators access and manage every case.

These are pure read helpers over the unit of work; the FastAPI dependencies in
``app.api.deps`` and the service layer call them and translate denials into a single,
**generic** ``PermissionDenied`` so a 403 never leaks a case's title, summary, counts,
sources, evidence, or even its existence (see ``docs/security.md`` rule on need-to-know).
"""

from __future__ import annotations

from uuid import UUID

from app.core.rbac import (
    CaseRole,
    MembershipStatus,
    Role,
    case_role_can_manage_members,
    case_role_can_mutate,
    case_role_can_read_material,
    case_role_can_review,
    case_role_can_view_audit,
)
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.user import CaseMemberRead

# A single generic message for every per-case denial. It intentionally reveals nothing
# about the case — not its title, contents, counts, or whether it exists at all.
FORBIDDEN_MESSAGE = "You do not have access to this case."


class CaseAccessService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    # --- identity ----------------------------------------------------------------

    def is_admin(self, principal: Principal) -> bool:
        return principal.role == Role.ADMIN

    def active_membership(self, principal: Principal, case_id: UUID) -> CaseMemberRead | None:
        """The principal's active membership in ``case_id``, or ``None``."""
        return self.uow.memberships.get_active(case_id, UUID(principal.id))

    def effective_case_role(self, principal: Principal, case_id: UUID) -> CaseRole | None:
        """The case role the principal effectively holds (admins act as case managers)."""
        if self.is_admin(principal):
            return CaseRole.CASE_MANAGER
        membership = self.active_membership(principal, case_id)
        return membership.case_role if membership else None

    def _active_memberships(self, principal: Principal) -> list[CaseMemberRead]:
        return [
            m
            for m in self.uow.memberships.for_user(UUID(principal.id))
            if m.status == MembershipStatus.ACTIVE
        ]

    def accessible_case_ids(self, principal: Principal) -> set[UUID] | None:
        """Case ids the principal may access. ``None`` means *all* (administrators)."""
        if self.is_admin(principal):
            return None
        return {m.case_id for m in self._active_memberships(principal)}

    def readable_case_ids(self, principal: Principal) -> set[UUID] | None:
        """Case ids whose raw material the principal may read (``None`` = all)."""
        if self.is_admin(principal):
            return None
        return {
            m.case_id
            for m in self._active_memberships(principal)
            if case_role_can_read_material(m.case_role)
        }

    def reviewable_case_ids(self, principal: Principal) -> set[UUID] | None:
        """Case ids where the principal may decide review items (``None`` = all)."""
        if self.is_admin(principal):
            return None
        return {
            m.case_id
            for m in self._active_memberships(principal)
            if case_role_can_review(m.case_role)
        }

    # --- predicates --------------------------------------------------------------

    def has_access(self, principal: Principal, case_id: UUID) -> bool:
        return self.is_admin(principal) or self.active_membership(principal, case_id) is not None

    def can_read_material(self, principal: Principal, case_id: UUID) -> bool:
        role = self.effective_case_role(principal, case_id)
        return role is not None and (self.is_admin(principal) or case_role_can_read_material(role))

    def can_mutate(self, principal: Principal, case_id: UUID) -> bool:
        role = self.effective_case_role(principal, case_id)
        return role is not None and (self.is_admin(principal) or case_role_can_mutate(role))

    def can_review(self, principal: Principal, case_id: UUID) -> bool:
        role = self.effective_case_role(principal, case_id)
        return role is not None and (self.is_admin(principal) or case_role_can_review(role))

    def can_view_audit(self, principal: Principal, case_id: UUID) -> bool:
        role = self.effective_case_role(principal, case_id)
        return role is not None and (self.is_admin(principal) or case_role_can_view_audit(role))

    def can_manage_members(self, principal: Principal, case_id: UUID) -> bool:
        role = self.effective_case_role(principal, case_id)
        return role is not None and (self.is_admin(principal) or case_role_can_manage_members(role))

    def can_view_reports(self, principal: Principal, case_id: UUID) -> bool:
        """Approved-report (export) access: any active member, or an administrator."""
        return self.has_access(principal, case_id)
