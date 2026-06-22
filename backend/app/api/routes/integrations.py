"""Integration diagnostics (v1.1).

Admin-only, read-only diagnostics for external integrations. Currently: the Foundry
connection health check, which reports enabled/configured/mode/result **without emitting
secrets**. This is a connection diagnostic, not a case action, so it is not case-audited.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import current_principal
from app.core.rbac import Role
from app.core.security import Principal
from app.foundry.config import FoundryConfig
from app.foundry.health import foundry_health
from app.services.errors import PermissionDenied

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/foundry/health", summary="Foundry connection health (admin-only; read-only)")
def foundry_health_endpoint(principal: Principal = Depends(current_principal)) -> dict:
    if principal.role != Role.ADMIN:
        raise PermissionDenied("Foundry diagnostics are restricted to administrators.")
    return foundry_health(FoundryConfig.from_env())
