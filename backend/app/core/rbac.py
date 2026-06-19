"""Role-based access control.

Six roles, least privilege, separation of duties. Authorization is enforced at the API
boundary (route guards) and re-checked in the service layer for decisions. See
``docs/v0.4_auth_rbac.md`` for the full role/permission matrix.
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
