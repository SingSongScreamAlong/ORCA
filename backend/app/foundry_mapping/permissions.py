"""ORCA → Foundry permission mapping (v0.9).

These rules are **derived from ORCA's real authorization predicates** (``app.core.rbac``
and the case-role helpers), so the exported spec cannot drift from what the system
actually enforces. A Foundry tenant would implement them as object/property-level
security and action gates: need-to-know by case membership, raw evidence restricted to
mutating roles, and partner export viewers limited to approved report packages.
"""

from __future__ import annotations

from app.core.rbac import (
    CaseRole,
    case_role_can_access_raw_files,
    case_role_can_manage_members,
    case_role_can_mutate,
    case_role_can_read_material,
    case_role_can_review,
    case_role_can_view_audit,
    case_role_can_view_reports,
)
from app.foundry_mapping.types import CaseRolePermission

_NOTES: dict[CaseRole, str] = {
    CaseRole.CASE_MANAGER: "Manages the case and its roster; full read/write on case material.",
    CaseRole.ANALYST: "Creates and curates case material; cannot decide reviews.",
    CaseRole.REVIEWER: "Decides review items; may also propose. No self-approval.",
    CaseRole.VIEWER: "Reads case material and approved reports; cannot mutate or read raw bytes.",
    CaseRole.PARTNER_EXPORT_VIEWER: (
        "Approved report packages only — never raw observations, evidence, graph, or audit."
    ),
}


def _permission(role: CaseRole) -> CaseRolePermission:
    return CaseRolePermission(
        case_role=role.value,
        can_read_material=case_role_can_read_material(role),
        can_mutate=case_role_can_mutate(role),
        can_review=case_role_can_review(role),
        can_manage_members=case_role_can_manage_members(role),
        can_view_audit=case_role_can_view_audit(role),
        can_access_raw_evidence=case_role_can_access_raw_files(role),
        can_view_approved_reports=case_role_can_view_reports(role),
        can_export_package=case_role_can_view_reports(role),
        notes=_NOTES.get(role, ""),
    )


CASE_ROLE_PERMISSIONS: tuple[CaseRolePermission, ...] = tuple(
    _permission(role) for role in CaseRole
)

# Non-case-role principals, for completeness in the exported permission spec.
GLOBAL_NOTES: dict[str, str] = {
    "admin": "Superuser: accesses and manages every case; the only role that may override "
    "the self-review control (audited).",
    "unassigned": "A user with no active membership in a case can do nothing with it — "
    "including learning whether it exists (generic 403).",
}
