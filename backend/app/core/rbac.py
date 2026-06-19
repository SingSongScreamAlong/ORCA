"""Role-based access control.

Six *global* roles, least privilege, separation of duties. RBAC answers "what kind of
user are you?". v0.6 adds **case membership** on top: a *case role* answers "which case
are you allowed to touch, and how?". A non-admin must hold an active membership in a
case to see or act on it (need-to-know). Authorization is enforced at the API boundary
(route guards) and re-checked in the service layer for decisions and case scoping. See
``docs/v0.4_auth_rbac.md`` and ``docs/v0.6_case_membership.md`` for the full matrices.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    CASE_MANAGER = "case_manager"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    PARTNER_EXPORT_VIEWER = "partner_export_viewer"


class CaseRole(str, Enum):
    """A user's role *within a specific case* (v0.6 case membership).

    A user holds one global :class:`Role`, but may be assigned a different case role per
    case. The case role decides what they may do *inside that case*; the global role
    still bounds what they may do at all (e.g. a viewer never gains review authority).
    """

    CASE_MANAGER = "case_manager"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    PARTNER_EXPORT_VIEWER = "partner_export_viewer"


class MembershipStatus(str, Enum):
    """Lifecycle of a case membership. Only ``active`` grants access."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class Capability(str, Enum):
    READ_CASE_MATERIAL = "read_case_material"  # cases, observations, evidence, relationships, review
    CREATE_CASE = "create_case"
    MANAGE_CASE = "manage_case"  # status changes, assignments
    CREATE_OBSERVATION = "create_observation"
    CREATE_EVIDENCE = "create_evidence"
    CREATE_RELATIONSHIP = "create_relationship"
    GENERATE_REPORT = "generate_report"
    PUBLISH_REPORT = "publish_report"
    REVIEW_DECIDE = "review_decide"  # approve / reject / needs_more_review / quarantine
    VIEW_AUDIT = "view_audit"
    VIEW_APPROVED_REPORTS = "view_approved_reports"  # published report packages
    ADMIN_OVERRIDE = "admin_override"  # bypass self-review, with a distinct audit event


_C = Capability

_ROLE_CAPABILITIES: dict[Role, set[Capability]] = {
    Role.ADMIN: set(Capability),  # the administrator may do anything
    Role.CASE_MANAGER: {
        _C.READ_CASE_MATERIAL, _C.CREATE_CASE, _C.MANAGE_CASE,
        _C.CREATE_OBSERVATION, _C.CREATE_EVIDENCE, _C.CREATE_RELATIONSHIP,
        _C.GENERATE_REPORT, _C.PUBLISH_REPORT, _C.VIEW_AUDIT, _C.VIEW_APPROVED_REPORTS,
    },
    Role.ANALYST: {
        _C.READ_CASE_MATERIAL, _C.CREATE_OBSERVATION, _C.CREATE_EVIDENCE,
        _C.CREATE_RELATIONSHIP, _C.GENERATE_REPORT, _C.VIEW_APPROVED_REPORTS,
    },
    # Reviewers may also propose intelligence; separation of duties is enforced on
    # *approval* (a reviewer cannot approve their own proposal — see rule 3).
    Role.REVIEWER: {
        _C.READ_CASE_MATERIAL, _C.CREATE_OBSERVATION, _C.CREATE_EVIDENCE,
        _C.REVIEW_DECIDE, _C.VIEW_AUDIT, _C.VIEW_APPROVED_REPORTS,
    },
    Role.VIEWER: {
        _C.READ_CASE_MATERIAL, _C.VIEW_APPROVED_REPORTS,
    },
    # Partner export viewers can ONLY access approved (published) report packages.
    Role.PARTNER_EXPORT_VIEWER: {
        _C.VIEW_APPROVED_REPORTS,
    },
}


def can(role: Role, capability: Capability) -> bool:
    """Return whether ``role`` is granted ``capability``."""
    return capability in _ROLE_CAPABILITIES.get(role, set())


def capabilities_for(role: Role) -> list[str]:
    """Return the sorted capability values for a role (for the API / UI)."""
    return sorted(c.value for c in _ROLE_CAPABILITIES.get(role, set()))


# --- Case roles (per-case authorization) ----------------------------------------

# The case role a user receives by default when assigned to (or auto-enrolled in) a
# case, derived from their global role. Callers may override it explicitly.
_DEFAULT_CASE_ROLE: dict[Role, CaseRole] = {
    Role.ADMIN: CaseRole.CASE_MANAGER,
    Role.CASE_MANAGER: CaseRole.CASE_MANAGER,
    Role.ANALYST: CaseRole.ANALYST,
    Role.REVIEWER: CaseRole.REVIEWER,
    Role.VIEWER: CaseRole.VIEWER,
    Role.PARTNER_EXPORT_VIEWER: CaseRole.PARTNER_EXPORT_VIEWER,
}

# Which case roles may read raw case material (observations, evidence, relationships,
# graph, drafts). The partner export viewer is deliberately excluded — they may only
# reach approved report packages.
_CASE_READ_ROLES: frozenset[CaseRole] = frozenset(
    {CaseRole.CASE_MANAGER, CaseRole.ANALYST, CaseRole.REVIEWER, CaseRole.VIEWER}
)
# Which case roles may create/modify case material within the case.
_CASE_MUTATION_ROLES: frozenset[CaseRole] = frozenset(
    {CaseRole.CASE_MANAGER, CaseRole.ANALYST, CaseRole.REVIEWER}
)
# Which case roles may decide review items (approve / reject / needs_more_review).
_CASE_REVIEW_ROLES: frozenset[CaseRole] = frozenset({CaseRole.REVIEWER})
# Which case roles may read the case audit log.
_CASE_AUDIT_ROLES: frozenset[CaseRole] = frozenset({CaseRole.CASE_MANAGER, CaseRole.REVIEWER})
# Which case roles may manage the case's membership roster.
_CASE_MANAGE_MEMBER_ROLES: frozenset[CaseRole] = frozenset({CaseRole.CASE_MANAGER})


def default_case_role(role: Role) -> CaseRole:
    """The case role assigned by default for a user with the given global role."""
    return _DEFAULT_CASE_ROLE.get(role, CaseRole.VIEWER)


def case_role_can_read_material(case_role: CaseRole) -> bool:
    return case_role in _CASE_READ_ROLES


def case_role_can_mutate(case_role: CaseRole) -> bool:
    return case_role in _CASE_MUTATION_ROLES


def case_role_can_review(case_role: CaseRole) -> bool:
    return case_role in _CASE_REVIEW_ROLES


def case_role_can_view_audit(case_role: CaseRole) -> bool:
    return case_role in _CASE_AUDIT_ROLES


def case_role_can_manage_members(case_role: CaseRole) -> bool:
    return case_role in _CASE_MANAGE_MEMBER_ROLES


def case_role_can_view_reports(case_role: CaseRole) -> bool:
    """Every active member may view that case's approved (published) reports."""
    return True
