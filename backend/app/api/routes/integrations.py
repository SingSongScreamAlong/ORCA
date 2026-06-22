"""Integration diagnostics + read-only import (v1.1–v1.4).

Admin-only access to Palantir Foundry from inside the app. Reads surface the connector's
data; the v1.4 import materialises Foundry objects as ORCA **entities** (the only write, and
only to ORCA's own store — never to Foundry):

* ``GET  /integrations/foundry/health``           — connection health (v1.1).
* ``GET  /integrations/foundry/discover``          — ontologies + object types (v1.3).
* ``GET  /integrations/foundry/object-types/{t}``  — object-type metadata (v1.3).
* ``GET  /integrations/foundry/objects/{t}``       — a small sample of objects (v1.3).
* ``GET  /integrations/foundry/objects/{t}/{id}``  — a single object by id (v1.3).
* ``POST /integrations/foundry/import``            — import objects as ORCA entities (v1.4).

All are **admin-only**. The reads are **read-only** against Foundry; the import reads Foundry
and writes only deduplicated ORCA entities (idempotent). They never emit secrets (the
connector's errors are secret-free, config is redacted). When Foundry is disabled (the default
for dev/CI), the deterministic **mock** client answers, and every response carries a ``mode``
field (``mock`` | ``real``) so the source is unambiguous.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.deps import current_principal, get_uow
from app.core.rbac import Role
from app.core.security import Principal
from app.foundry.client import build_foundry_client
from app.foundry.config import FoundryConfig
from app.foundry.errors import FoundryConfigError, FoundryError
from app.foundry.health import foundry_health
from app.foundry.import_service import FoundryImportService
from app.repositories.uow import UnitOfWork
from app.schemas.foundry import FoundryImportRequest, FoundryImportResult
from app.services.errors import PermissionDenied

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _require_admin(principal: Principal) -> None:
    if principal.role != Role.ADMIN:
        raise PermissionDenied("Foundry diagnostics are restricted to administrators.")


def _client():
    """Build the active Foundry client (mock when disabled; real when enabled)."""
    return build_foundry_client(FoundryConfig.from_env())


def _safe_call(fn):
    """Run a read and translate connector errors into safe HTTP responses (no secrets)."""
    try:
        return fn()
    except FoundryConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FoundryError as exc:  # network/HTTP/upstream — message is written to be secret-free
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/foundry/health", summary="Foundry connection health (admin-only; read-only)")
def foundry_health_endpoint(principal: Principal = Depends(current_principal)) -> dict:
    _require_admin(principal)
    return foundry_health(FoundryConfig.from_env())


@router.get("/foundry/discover", summary="List Foundry ontologies + object types (admin-only)")
def foundry_discover_endpoint(principal: Principal = Depends(current_principal)) -> dict:
    _require_admin(principal)
    client = _client()
    out: dict = {"mode": client.mode}
    out["ontologies"] = _safe_call(client.list_ontologies)
    cfg = FoundryConfig.from_env()
    if cfg.ontology_api_name or client.mode == "mock":
        out["object_types"] = _safe_call(client.list_object_types)
    return out


@router.get(
    "/foundry/object-types/{object_type}",
    summary="Foundry object-type metadata (admin-only; read-only)",
)
def foundry_object_type_endpoint(
    object_type: str = Path(..., description="Object type API name, e.g. OrcaCase"),
    principal: Principal = Depends(current_principal),
) -> dict:
    _require_admin(principal)
    client = _client()
    return {"mode": client.mode, "object_type": object_type,
            "metadata": _safe_call(lambda: client.get_object_type_metadata(object_type))}


@router.get(
    "/foundry/objects/{object_type}",
    summary="A small sample of Foundry objects (admin-only; read-only)",
)
def foundry_objects_endpoint(
    object_type: str = Path(..., description="Object type API name, e.g. OrcaCase"),
    limit: int = Query(10, ge=1, le=50, description="Max objects to read (1–50)"),
    principal: Principal = Depends(current_principal),
) -> dict:
    _require_admin(principal)
    client = _client()
    objects = _safe_call(lambda: client.list_demo_objects(object_type, limit=limit))
    return {"mode": client.mode, "object_type": object_type, "count": len(objects), "objects": objects}


@router.get(
    "/foundry/objects/{object_type}/{object_id}",
    summary="A single Foundry object by id (admin-only; read-only)",
)
def foundry_object_by_id_endpoint(
    object_type: str = Path(..., description="Object type API name, e.g. OrcaCase"),
    object_id: str = Path(..., description="Primary key / id of the object"),
    principal: Principal = Depends(current_principal),
) -> dict:
    _require_admin(principal)
    client = _client()
    return {"mode": client.mode, "object_type": object_type, "object_id": object_id,
            "object": _safe_call(lambda: client.get_object_by_id(object_type, object_id))}


@router.post(
    "/foundry/import",
    response_model=FoundryImportResult,
    summary="Import Foundry objects as ORCA entities (admin-only; read-only against Foundry)",
)
def foundry_import_endpoint(
    payload: FoundryImportRequest,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> FoundryImportResult:
    _require_admin(principal)
    client = _client()
    service = FoundryImportService(uow, client)
    return _safe_call(lambda: service.import_entities(payload, principal))
