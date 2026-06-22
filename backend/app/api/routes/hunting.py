"""Hunting Grounds — source/NAI registry endpoints.

The governance gate from ``docs/hunting_grounds_charter.md``, in code. Operators **propose**
candidate sources; only an **administrator** can move one through the lifecycle, and a source
can be **authorized only with a complete lawful-basis record**. Nothing here monitors or
collects — it governs *which* sources may ever be monitored.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import current_principal, get_uow, require
from app.core.rbac import Capability, Role
from app.core.security import Principal
from app.models.enums import HuntingEscalationStatus, HuntingSourceStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    HuntingAuthorize,
    HuntingDecision,
    HuntingDiscoveryResult,
    HuntingDiscoveryRun,
    HuntingLeadCreate,
    HuntingSourcePropose,
    HuntingSourceRead,
    HuntingSummary,
)
from app.schemas.hunting_escalation import (
    HuntingEscalationDecision,
    HuntingEscalationRaise,
    HuntingEscalationRead,
    HuntingEscalationReport,
)
from app.schemas.observation import ObservationRead
from app.services.errors import PermissionDenied
from app.services.hunting_escalation_service import HuntingEscalationService
from app.services.hunting_lead_service import HuntingLeadService
from app.services.hunting_registry_service import HuntingRegistryService

router = APIRouter(prefix="/hunting", tags=["hunting-grounds"])


def _require_admin(principal: Principal) -> None:
    # Authorizing/monitoring a source is the legal gate — administrators only.
    if principal.role != Role.ADMIN:
        raise PermissionDenied("Hunting Grounds source decisions are restricted to administrators.")


@router.get("/summary", response_model=HuntingSummary, summary="AOR rollup of the source registry")
def hunting_summary(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
) -> HuntingSummary:
    return HuntingRegistryService().summary()


@router.post(
    "/discovery/run",
    response_model=HuntingDiscoveryResult,
    summary="Propose discovered candidate venues into the registry (dedup'd; proposes only)",
)
def run_discovery(
    payload: HuntingDiscoveryRun,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
) -> HuntingDiscoveryResult:
    return HuntingRegistryService().run_discovery(payload, principal)


@router.get("/sources", response_model=list[HuntingSourceRead], summary="List Hunting Grounds sources")
def list_sources(
    status_filter: HuntingSourceStatus | None = Query(None, alias="status"),
    aor: str | None = Query(None),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
) -> list[HuntingSourceRead]:
    return HuntingRegistryService().list(status=status_filter, aor=aor)


@router.post(
    "/sources",
    response_model=HuntingSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a candidate source (enters as 'proposed' — not monitored)",
)
def propose_source(
    payload: HuntingSourcePropose,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
) -> HuntingSourceRead:
    return HuntingRegistryService().propose(payload, principal)


@router.get("/sources/{source_id}", response_model=HuntingSourceRead, summary="Get a source")
def get_source(
    source_id: UUID,
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
) -> HuntingSourceRead:
    return HuntingRegistryService().get(source_id)


@router.post(
    "/sources/{source_id}/authorize",
    response_model=HuntingSourceRead,
    summary="Authorize a source for monitoring (admin-only; requires a lawful-basis record)",
)
def authorize_source(
    source_id: UUID,
    payload: HuntingAuthorize,
    principal: Principal = Depends(current_principal),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService().authorize(source_id, payload, principal)


@router.post(
    "/sources/{source_id}/reject",
    response_model=HuntingSourceRead,
    summary="Reject a proposed source (admin-only)",
)
def reject_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService().reject(source_id, payload.reason, principal)


@router.post(
    "/sources/{source_id}/monitor",
    response_model=HuntingSourceRead,
    summary="Begin monitoring an authorized source (admin-only)",
)
def monitor_source(
    source_id: UUID,
    principal: Principal = Depends(current_principal),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService().start_monitoring(source_id, principal)


@router.post(
    "/sources/{source_id}/suspend",
    response_model=HuntingSourceRead,
    summary="Suspend an authorized/monitored source (admin-only)",
)
def suspend_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService().suspend(source_id, payload.reason, principal)


@router.post(
    "/sources/{source_id}/retire",
    response_model=HuntingSourceRead,
    summary="Retire a source (admin-only)",
)
def retire_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService().retire(source_id, payload.reason, principal)


@router.post(
    "/sources/{source_id}/leads",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a text-only lead from a monitored source (→ proposed observation in review)",
)
def ingest_lead(
    source_id: UUID,
    payload: HuntingLeadCreate,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> ObservationRead:
    return HuntingLeadService(uow).ingest(source_id, payload, principal)


# --- suspected-minor / CSAM escalation (report-only, never-store) ----------------


@router.post(
    "/escalations",
    response_model=HuntingEscalationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a suspected-minor/CSAM concern (report-only; stores no material)",
)
def raise_escalation(
    payload: HuntingEscalationRaise,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
) -> HuntingEscalationRead:
    return HuntingEscalationService().raise_concern(payload, principal)


@router.get(
    "/escalations",
    response_model=list[HuntingEscalationRead],
    summary="List escalations (admin-only)",
)
def list_escalations(
    status_filter: HuntingEscalationStatus | None = Query(None, alias="status"),
    principal: Principal = Depends(current_principal),
) -> list[HuntingEscalationRead]:
    _require_admin(principal)
    return HuntingEscalationService().list(status=status_filter)


@router.post(
    "/escalations/{escalation_id}/report",
    response_model=HuntingEscalationRead,
    summary="Record that an NCMEC CyberTipline report was filed (admin-only)",
)
def report_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationReport,
    principal: Principal = Depends(current_principal),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService().report(escalation_id, payload.ncmec_reference, principal)


@router.post(
    "/escalations/{escalation_id}/close",
    response_model=HuntingEscalationRead,
    summary="Close a reported escalation (admin-only)",
)
def close_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationDecision,
    principal: Principal = Depends(current_principal),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService().close(escalation_id, payload.reason, principal)


@router.post(
    "/escalations/{escalation_id}/dismiss",
    response_model=HuntingEscalationRead,
    summary="Dismiss an escalation found not to be CSAM (admin-only)",
)
def dismiss_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationDecision,
    principal: Principal = Depends(current_principal),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService().dismiss(escalation_id, payload.reason, principal)
