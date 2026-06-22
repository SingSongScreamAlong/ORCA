"""Hunting Grounds — source/NAI registry endpoints.

The governance gate from ``docs/hunting_grounds_charter.md``, in code. Operators **propose**
candidate sources; only an **administrator** can move one through the lifecycle, and a source
can be **authorized only with a complete lawful-basis record**. Nothing here monitors or
collects — it governs *which* sources may ever be monitored.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import current_principal, get_uow, require
from app.core.rbac import Capability, Role
from app.core.security import Principal
from app.models.enums import EntityType, HuntingEscalationStatus, HuntingSourceStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    AorReferralPackage,
    HuntingAuthorize,
    HuntingCollectionResult,
    HuntingCollectionStatus,
    HuntingCollectionSweepResult,
    HuntingDecision,
    HuntingDiscoveryResult,
    HuntingDiscoveryRun,
    HuntingDiscoveryScheduleStatus,
    HuntingDiscoveryStatus,
    HuntingDiscoverySweepResult,
    HuntingIntelPicture,
    HuntingLeadCreate,
    HuntingLinkResult,
    HuntingReferralPackage,
    HuntingSourcePropose,
    HuntingSourceRead,
    HuntingSummary,
    HuntingWatchlistAdd,
    HuntingWatchlistEntry,
    IdentifierDossier,
    IdentifierReferralPackage,
)
from app.schemas.hunting_escalation import (
    HuntingEscalationDecision,
    HuntingEscalationRaise,
    HuntingEscalationRead,
    HuntingEscalationReport,
)
from app.schemas.observation import ObservationRead
from app.services.errors import PermissionDenied
from app.services.hunting_collection import (
    CollectionConfigError,
    CollectionError,
    CollectionNotEnabled,
    HuntingCollectionService,
)
from app.services.hunting_discovery import (
    DiscoveryConfigError,
    DiscoveryError,
    DiscoveryNotEnabled,
    HuntingDiscoveryService,
)
from app.services.hunting_escalation_service import HuntingEscalationService
from app.services.hunting_intel_service import HuntingIntelService
from app.services.hunting_lead_service import HuntingLeadService
from app.services.hunting_link_service import HuntingLinkService
from app.services.hunting_referral_service import HuntingReferralService
from app.services.hunting_registry_service import HuntingRegistryService
from app.services.hunting_scheduler import scheduler
from app.services.hunting_watchlist_service import HuntingWatchlistService

router = APIRouter(prefix="/hunting", tags=["hunting-grounds"])


def _require_admin(principal: Principal) -> None:
    # Authorizing/monitoring a source is the legal gate — administrators only.
    if principal.role != Role.ADMIN:
        raise PermissionDenied("Hunting Grounds source decisions are restricted to administrators.")


@router.get("/summary", response_model=HuntingSummary, summary="AOR rollup of the source registry")
def hunting_summary(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSummary:
    return HuntingRegistryService(uow).summary()


@router.get(
    "/intel",
    response_model=HuntingIntelPicture,
    summary="AOR intelligence — cross-venue identifier links (read-only; pointers/metadata only)",
)
def hunting_intel(
    aor: str | None = Query(None, description="Scope to one AOR; omit for all monitored venues."),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingIntelPicture:
    """The common operating picture: which located identifiers recur across two or more monitored
    venues (the strongest case-building leads). Read-only — proposes nothing."""
    return HuntingIntelService(uow).picture(aor)


@router.get(
    "/intel/identifier",
    response_model=IdentifierDossier,
    summary="Pivot: everywhere one located identifier appears across monitored venues",
)
def identifier_dossier(
    type: EntityType = Query(..., description="Identifier type (e.g. phone, username, crypto_address)."),
    value: str = Query(..., min_length=1, description="The identifier value to pivot on."),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> IdentifierDossier:
    """Where does this one phone/wallet/handle/.onion appear? Returns every monitored venue it was
    located from, the text leads, the AORs, and the identifiers it co-occurs with — the per-identifier
    pivot that assembles an LE referral. Read-only; `404` if the identifier was never located."""
    dossier = HuntingIntelService(uow).identifier_dossier(type, value)
    if dossier is None:
        raise HTTPException(status_code=404, detail="No such located identifier.")
    return dossier


@router.get(
    "/intel/identifier/referral",
    response_model=IdentifierReferralPackage,
    summary="Generate an LE referral dossier for one located identifier (cross-venue; no media)",
)
def identifier_referral(
    type: EntityType = Query(..., description="Identifier type (e.g. phone, username, crypto_address)."),
    value: str = Query(..., min_length=1, description="The identifier value to refer."),
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> IdentifierReferralPackage:
    """The per-identifier referral: assemble every monitored venue this one identifier was located
    from (with lawful basis), the text leads, co-occurring identifiers, and relationships into a
    dossier for LE. Pointers/metadata only — no media. `404` if never located. Audited."""
    pkg = HuntingReferralService(uow).build_for_identifier(type, value, principal)
    if pkg is None:
        raise HTTPException(status_code=404, detail="No such located identifier.")
    return pkg


@router.get(
    "/intel/aor/referral",
    response_model=AorReferralPackage,
    summary="Generate an LE operation rollup for a whole AOR (cross-venue case file; no media)",
)
def aor_referral(
    aor: str = Query(..., min_length=1, description="Area of responsibility to roll up."),
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> AorReferralPackage:
    """The AOR operation rollup: consolidate every monitored venue in the region (with lawful
    basis), all located identifiers, the cross-venue links tying venues into one operation, and the
    relationship map into a single LE dossier. Pointers/metadata only — no media. Audited."""
    return HuntingReferralService(uow).build_for_aor(aor, principal)


@router.post(
    "/links/propose",
    response_model=HuntingLinkResult,
    summary="Propose cross-venue links from approved leads into the review queue (analysts decide)",
)
def propose_links(
    aor: str | None = Query(None, description="Scope to one AOR; omit for all monitored venues."),
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingLinkResult:
    """For identifier pairs that co-occur in approved leads across two or more monitored venues,
    propose an `appears_with` relationship into the review queue. Only approved observations are
    cited; nothing is auto-confirmed; existing links are not re-proposed."""
    return HuntingLinkService(uow).propose_links(principal, aor=aor)


# --- operator-managed AOR watchlist (the autonomous cadence's targets) -----------


@router.get(
    "/watchlist",
    response_model=list[HuntingWatchlistEntry],
    summary="The operator-managed AOR watchlist the cadence sweeps",
)
def list_watchlist(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[HuntingWatchlistEntry]:
    return HuntingWatchlistService(uow).list()


@router.post(
    "/watchlist",
    response_model=HuntingWatchlistEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Add an AOR to the watchlist (admin-only)",
)
def add_watchlist(
    payload: HuntingWatchlistAdd,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingWatchlistEntry:
    _require_admin(principal)
    return HuntingWatchlistService(uow).add(payload.aor, principal)


@router.delete(
    "/watchlist/{aor}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an AOR from the watchlist (admin-only)",
)
def remove_watchlist(
    aor: str,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> None:
    _require_admin(principal)
    HuntingWatchlistService(uow).remove(aor, principal)


@router.post(
    "/discovery/run",
    response_model=HuntingDiscoveryResult,
    summary="Propose discovered candidate venues into the registry (dedup'd; proposes only)",
)
def run_discovery(
    payload: HuntingDiscoveryRun,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingDiscoveryResult:
    return HuntingRegistryService(uow).run_discovery(payload, principal)


@router.get(
    "/discovery/status",
    response_model=HuntingDiscoveryStatus,
    summary="Autonomous discovery posture (provider/enabled/configured; never the API key)",
)
def discovery_status(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingDiscoveryStatus:
    return HuntingDiscoveryService(uow).status()


@router.post(
    "/discovery/auto",
    response_model=HuntingDiscoveryResult,
    summary="Autonomously seek new venues via the configured lawful source (proposes only)",
)
def auto_discovery(
    aor: str = Query(..., min_length=1, description="Area of responsibility to seek within."),
    limit: int = Query(10, ge=1, le=50, description="Maximum candidates to seek this pass."),
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingDiscoveryResult:
    """Reach out through the configured, licensed discovery source and propose what it finds.

    Every candidate enters as ``proposed`` (deduped by URL); an administrator still authorizes
    each with a lawful basis before anything is monitored. Disabled by default — returns a clear
    400 until ``ORCA_HUNTING_DISCOVERY_PROVIDER`` is configured. Errors carry no secrets.
    """
    try:
        return HuntingDiscoveryService(uow).auto_discover(aor, principal, limit=limit)
    except (DiscoveryNotEnabled, DiscoveryConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DiscoveryError as exc:  # network/HTTP/parse — message is written to be secret-free
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/discovery/sweep",
    response_model=HuntingDiscoverySweepResult,
    summary="Autonomously seek across a list of AORs in one pass (the watchlist; proposes only)",
)
def auto_discovery_sweep(
    aors: str | None = Query(
        None, description="Comma-separated AORs to sweep; defaults to the configured watchlist."
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum candidates per AOR this pass."),
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingDiscoverySweepResult:
    """Seek across many areas at once — the whole region in a single autonomous pass.

    Each candidate enters as ``proposed`` (deduped by URL, across AORs and re-runs); an
    administrator still authorizes each before monitoring. With no ``aors`` and no configured
    watchlist, returns a clear 400. Errors carry no secrets.
    """
    aor_list = [a.strip() for a in aors.split(",") if a.strip()] if aors else None
    try:
        return HuntingDiscoveryService(uow).sweep(principal, aors=aor_list, limit_per_aor=limit)
    except (DiscoveryNotEnabled, DiscoveryConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DiscoveryError as exc:  # network/HTTP/parse — message is written to be secret-free
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# --- continuous (scheduled) discovery — the autonomous cadence -------------------


@router.get(
    "/discovery/schedule",
    response_model=HuntingDiscoveryScheduleStatus,
    summary="Continuous discovery posture (enabled/paused/running, interval, last run)",
)
def discovery_schedule_status(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
) -> HuntingDiscoveryScheduleStatus:
    return scheduler.status()


@router.post(
    "/discovery/schedule/pause",
    response_model=HuntingDiscoveryScheduleStatus,
    summary="Kill-switch: pause the continuous discovery cadence (admin-only)",
)
def pause_discovery_schedule(
    principal: Principal = Depends(current_principal),
) -> HuntingDiscoveryScheduleStatus:
    _require_admin(principal)
    scheduler.paused = True
    return scheduler.status()


@router.post(
    "/discovery/schedule/resume",
    response_model=HuntingDiscoveryScheduleStatus,
    summary="Resume the continuous discovery cadence (admin-only)",
)
def resume_discovery_schedule(
    principal: Principal = Depends(current_principal),
) -> HuntingDiscoveryScheduleStatus:
    _require_admin(principal)
    scheduler.paused = False
    return scheduler.status()


@router.post(
    "/discovery/schedule/run-now",
    response_model=HuntingDiscoverySweepResult,
    summary="Trigger one discovery sweep immediately and record it (admin-only)",
)
def run_discovery_schedule_now(
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingDiscoverySweepResult:
    """Run the cadence's sweep once, right now, attributed to the triggering administrator.

    Honours the same config as the loop (watchlist + per-AOR limit) and updates the schedule's
    last-run record. Returns `400` when disabled/misconfigured, `502` on an upstream failure.
    """
    _require_admin(principal)
    config = scheduler.config()
    try:
        sweep = HuntingDiscoveryService(uow).sweep(principal, limit_per_aor=config.limit_per_aor)
    except (DiscoveryNotEnabled, DiscoveryConfigError) as exc:
        scheduler.record_error(str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DiscoveryError as exc:
        scheduler.record_error(str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    scheduler.record_run(sweep)
    return sweep


# --- automated collection (monitored sources → proposed observations) ------------


@router.get(
    "/collection/status",
    response_model=HuntingCollectionStatus,
    summary="Automated collection posture (provider/enabled/configured; never the API key)",
)
def collection_status(
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingCollectionStatus:
    return HuntingCollectionService(uow).status()


@router.post(
    "/collection/run",
    response_model=HuntingCollectionSweepResult,
    summary="Collect text leads from all monitored sources → proposed observations (proposes only)",
)
def run_collection(
    limit: int = Query(10, ge=1, le=50, description="Maximum leads per source this pass."),
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingCollectionSweepResult:
    """Pull text-only candidate leads from every monitored source and propose each as an
    observation in the review queue. CSAM-safe (no media field); analysts decide. Disabled by
    default — returns a clear 400 until configured; 502 on an upstream failure."""
    try:
        return HuntingCollectionService(uow).collect_all(principal, limit_per_source=limit)
    except (CollectionNotEnabled, CollectionConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CollectionError as exc:  # network/HTTP/parse — message is written to be secret-free
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sources", response_model=list[HuntingSourceRead], summary="List Hunting Grounds sources")
def list_sources(
    status_filter: HuntingSourceStatus | None = Query(None, alias="status"),
    aor: str | None = Query(None),
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[HuntingSourceRead]:
    return HuntingRegistryService(uow).list(status=status_filter, aor=aor)


@router.post(
    "/sources",
    response_model=HuntingSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a candidate source (enters as 'proposed' — not monitored)",
)
def propose_source(
    payload: HuntingSourcePropose,
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    return HuntingRegistryService(uow).propose(payload, principal)


@router.get("/sources/{source_id}", response_model=HuntingSourceRead, summary="Get a source")
def get_source(
    source_id: UUID,
    _: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    return HuntingRegistryService(uow).get(source_id)


@router.post(
    "/sources/{source_id}/authorize",
    response_model=HuntingSourceRead,
    summary="Authorize a source for monitoring (admin-only; requires a lawful-basis record)",
)
def authorize_source(
    source_id: UUID,
    payload: HuntingAuthorize,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService(uow).authorize(source_id, payload, principal)


@router.post(
    "/sources/{source_id}/reject",
    response_model=HuntingSourceRead,
    summary="Reject a proposed source (admin-only)",
)
def reject_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService(uow).reject(source_id, payload.reason, principal)


@router.post(
    "/sources/{source_id}/monitor",
    response_model=HuntingSourceRead,
    summary="Begin monitoring an authorized source (admin-only)",
)
def monitor_source(
    source_id: UUID,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService(uow).start_monitoring(source_id, principal)


@router.post(
    "/sources/{source_id}/suspend",
    response_model=HuntingSourceRead,
    summary="Suspend an authorized/monitored source (admin-only)",
)
def suspend_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService(uow).suspend(source_id, payload.reason, principal)


@router.post(
    "/sources/{source_id}/retire",
    response_model=HuntingSourceRead,
    summary="Retire a source (admin-only)",
)
def retire_source(
    source_id: UUID,
    payload: HuntingDecision,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingSourceRead:
    _require_admin(principal)
    return HuntingRegistryService(uow).retire(source_id, payload.reason, principal)


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


@router.post(
    "/sources/{source_id}/collect",
    response_model=HuntingCollectionResult,
    summary="Automatically collect text leads from one monitored source (→ proposed observations)",
)
def collect_source(
    source_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Maximum leads to collect this pass."),
    principal: Principal = Depends(require(Capability.CREATE_OBSERVATION)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingCollectionResult:
    """Pull text-only candidate leads from a single monitored source and propose each as an
    observation in the review queue. 422 if the source isn't monitored; 400 if collection is
    disabled/misconfigured; 502 on an upstream failure. CSAM-safe; analysts decide."""
    try:
        return HuntingCollectionService(uow).collect(source_id, principal, limit=limit)
    except (CollectionNotEnabled, CollectionConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CollectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/sources/{source_id}/referral",
    response_model=HuntingReferralPackage,
    summary="Generate a law-enforcement referral dossier for a source (pointers/metadata; no media)",
)
def source_referral(
    source_id: UUID,
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingReferralPackage:
    """Aggregate the located identifiers, text leads, and relationship map for a source into a
    referral package for LE — provenance + lawful basis included, no media. Audited."""
    return HuntingReferralService(uow).build(source_id, principal)


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
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingEscalationRead:
    return HuntingEscalationService(uow).raise_concern(payload, principal)


@router.get(
    "/escalations",
    response_model=list[HuntingEscalationRead],
    summary="List escalations (admin-only)",
)
def list_escalations(
    status_filter: HuntingEscalationStatus | None = Query(None, alias="status"),
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> list[HuntingEscalationRead]:
    _require_admin(principal)
    return HuntingEscalationService(uow).list(status=status_filter)


@router.post(
    "/escalations/{escalation_id}/report",
    response_model=HuntingEscalationRead,
    summary="Record that an NCMEC CyberTipline report was filed (admin-only)",
)
def report_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationReport,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService(uow).report(escalation_id, payload.ncmec_reference, principal)


@router.post(
    "/escalations/{escalation_id}/close",
    response_model=HuntingEscalationRead,
    summary="Close a reported escalation (admin-only)",
)
def close_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationDecision,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService(uow).close(escalation_id, payload.reason, principal)


@router.post(
    "/escalations/{escalation_id}/dismiss",
    response_model=HuntingEscalationRead,
    summary="Dismiss an escalation found not to be CSAM (admin-only)",
)
def dismiss_escalation(
    escalation_id: UUID,
    payload: HuntingEscalationDecision,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> HuntingEscalationRead:
    _require_admin(principal)
    return HuntingEscalationService(uow).dismiss(escalation_id, payload.reason, principal)
