"""Case endpoints — the analyst's workspace.

A case bundles the analyst loop: observations, relationships, timeline, audit log, and
report drafts. The case is a view over evidence; it never owns it.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import current_principal, get_uow
from app.core.security import Principal
from app.models.enums import ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.audit import AuditEntryRead
from app.schemas.case import CaseCreate, CaseDetail, CaseRead
from app.schemas.evidence import EvidenceItemRead
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.report import ReportRead
from app.schemas.timeline import TimelineEvent
from app.services.case_service import CaseService
from app.services.evidence_service import EvidenceService
from app.services.observation_service import ObservationService
from app.services.relationship_service import RelationshipService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseRead], summary="List cases")
def list_cases(uow: UnitOfWork = Depends(get_uow)) -> list[CaseRead]:
    return CaseService(uow).list()


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED, summary="Create a case")
def create_case(
    payload: CaseCreate,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseRead:
    return CaseService(uow).create(payload, principal)


@router.get("/{case_id}", response_model=CaseDetail, summary="Case overview with counts")
def get_case(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> CaseDetail:
    return CaseService(uow).detail(case_id)


@router.get(
    "/{case_id}/observations",
    response_model=list[ObservationRead],
    summary="Observations in a case",
)
def case_observations(
    case_id: UUID,
    status_filter: ReviewStatus | None = Query(None, alias="status"),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ObservationRead]:
    CaseService(uow).get(case_id)  # 404 if missing
    return ObservationService(uow).list(case_id=case_id, status=status_filter, limit=1000)


@router.get(
    "/{case_id}/relationships",
    response_model=list[RelationshipRead],
    summary="Relationships in a case",
)
def case_relationships(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> list[RelationshipRead]:
    CaseService(uow).get(case_id)
    return RelationshipService(uow).list(case_id=case_id, limit=1000)


@router.get(
    "/{case_id}/evidence",
    response_model=list[EvidenceItemRead],
    summary="Evidence items in a case (the evidence locker)",
)
def case_evidence(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> list[EvidenceItemRead]:
    return EvidenceService(uow).list_for_case(case_id)


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent], summary="Case timeline")
def case_timeline(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> list[TimelineEvent]:
    return TimelineService(uow).for_case(case_id)


@router.get("/{case_id}/audit", response_model=list[AuditEntryRead], summary="Case audit log")
def case_audit(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> list[AuditEntryRead]:
    entries = CaseService(uow).audit(case_id)
    return [AuditEntryRead.model_validate(e) for e in entries]


@router.get("/{case_id}/reports", response_model=list[ReportRead], summary="Report drafts for a case")
def case_reports(case_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> list[ReportRead]:
    CaseService(uow).get(case_id)
    return ReportService(uow).list(case_id)


@router.post(
    "/{case_id}/report",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a draft report from approved evidence",
)
def generate_report(
    case_id: UUID,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> ReportRead:
    return ReportService(uow).generate_draft(case_id, principal)
