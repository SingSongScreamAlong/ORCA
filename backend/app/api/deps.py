"""Shared API dependencies: pagination, the unit of work, authentication, and the
capability-based route guard."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, Path, Query

from app.core.rbac import Capability, CaseRole, can
from app.core.security import Principal, resolve_principal
from app.repositories.uow import UnitOfWork, build_unit_of_work
from app.services.case_access import FORBIDDEN_MESSAGE, CaseAccessService


def get_uow() -> Iterator[UnitOfWork]:
    """Yield a request-scoped unit of work, committing on success."""
    uow = build_unit_of_work()
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()


def current_principal(
    x_orca_user: str | None = Header(default=None, alias="X-ORCA-User"),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Resolve the authenticated principal from the ``X-ORCA-User`` header (dev auth)."""
    return resolve_principal(x_orca_user, uow)


def require(capability: Capability) -> Callable[..., Principal]:
    """Return a dependency that requires ``capability`` and yields the principal.

    A missing capability raises ``PermissionDenied`` (HTTP 403).
    """

    def guard(principal: Principal = Depends(current_principal)) -> Principal:
        if not can(principal.role, capability):
            from app.services.errors import PermissionDenied

            raise PermissionDenied(
                f"Role '{principal.role.value}' is not permitted to {capability.value.replace('_', ' ')}."
            )
        return principal

    return guard


# --- Per-case authorization (v0.6) ----------------------------------------------
#
# These guards read ``case_id`` from the path and enforce case membership on top of
# RBAC. Every denial raises the *same* generic 403 so it never reveals a case's title,
# contents, counts, or existence. Mutations that carry the case id in the request body
# (e.g. POST /observations) are checked in the service layer instead, where the case is
# known; these dependencies cover the case-keyed (``/cases/{case_id}/...``) routes.


def _forbid_case() -> None:
    from app.services.errors import PermissionDenied

    raise PermissionDenied(FORBIDDEN_MESSAGE)


def require_case_access(
    case_id: UUID = Path(...),
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Require an active membership in the case (administrators access every case)."""
    if not CaseAccessService(uow).has_access(principal, case_id):
        _forbid_case()
    return principal


def require_case_role(*allowed: CaseRole) -> Callable[..., Principal]:
    """Require the principal's effective case role to be one of ``allowed`` (admin ok)."""

    def guard(
        case_id: UUID = Path(...),
        principal: Principal = Depends(current_principal),
        uow: UnitOfWork = Depends(get_uow),
    ) -> Principal:
        access = CaseAccessService(uow)
        role = access.effective_case_role(principal, case_id)
        if not access.is_admin(principal) and (role is None or role not in allowed):
            _forbid_case()
        return principal

    return guard


def require_case_material_read(
    case_id: UUID = Path(...),
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Read raw case material: global READ_CASE_MATERIAL plus active, reading membership."""
    if not CaseAccessService(uow).can_read_material(principal, case_id):
        _forbid_case()
    return principal


def require_case_mutation(
    case_id: UUID = Path(...),
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Create/modify case material: an active membership with a mutating case role."""
    if not CaseAccessService(uow).can_mutate(principal, case_id):
        _forbid_case()
    return principal


def require_case_review(
    case_id: UUID = Path(...),
    principal: Principal = Depends(require(Capability.REVIEW_DECIDE)),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Decide review items: global REVIEW_DECIDE plus reviewer membership in the case."""
    if not CaseAccessService(uow).can_review(principal, case_id):
        _forbid_case()
    return principal


def require_case_audit_access(
    case_id: UUID = Path(...),
    principal: Principal = Depends(require(Capability.VIEW_AUDIT)),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Read the case audit log: global VIEW_AUDIT plus an auditing case role."""
    if not CaseAccessService(uow).can_view_audit(principal, case_id):
        _forbid_case()
    return principal


def require_case_export_access(
    case_id: UUID = Path(...),
    principal: Principal = Depends(require(Capability.VIEW_APPROVED_REPORTS)),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Access approved reports/exports for the case (any active member; partner-safe)."""
    if not CaseAccessService(uow).can_view_reports(principal, case_id):
        _forbid_case()
    return principal


def require_case_membership_management(
    case_id: UUID = Path(...),
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> Principal:
    """Manage the case roster: an administrator or the case's assigned case manager."""
    if not CaseAccessService(uow).can_manage_members(principal, case_id):
        _forbid_case()
    return principal


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return."),
    offset: int = Query(0, ge=0, description="Items to skip."),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
