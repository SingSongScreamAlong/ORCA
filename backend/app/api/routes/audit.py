"""System-wide audit log (admin-only).

The per-case audit endpoint (`GET /cases/{id}/audit`) is scoped to a case for need-to-know.
This admin-only view returns the full append-only log — including **connection/integration
actions that are not tied to a single case**, such as Hunting Grounds source decisions,
escalations, and Foundry reads. It never mutates anything.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import current_principal, get_uow
from app.core.rbac import Role
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.audit import AuditEntryRead
from app.services.errors import PermissionDenied

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryRead], summary="System audit log (admin-only)")
def system_audit(
    action_prefix: str | None = Query(
        None, description="Filter to actions starting with this prefix, e.g. 'hunting.'."
    ),
    limit: int = Query(100, ge=1, le=500),
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> list[AuditEntryRead]:
    if principal.role != Role.ADMIN:
        raise PermissionDenied("The system audit log is restricted to administrators.")
    entries = uow.audit.list()  # newest first; all cases (and case-less integration actions)
    if action_prefix:
        entries = [e for e in entries if e.action.startswith(action_prefix)]
    return [AuditEntryRead.model_validate(e) for e in entries[:limit]]
