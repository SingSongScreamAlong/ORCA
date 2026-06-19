"""Case endpoints — the analyst's workspace, guarded by RBAC and case membership.

Reads of a case's material require an active, reading membership (admins see all). The
list endpoint is scoped to the caller's cases. Every denial is a generic 403 that does
not reveal whether the case exists. See ``docs/v0.6_case_membership.md``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import (
    get_uow,
    require,
    require_case_access,
    require_case_audit_access,
    require_case_material_read,
    require_case_membership_management,
)
from app.core.config import get_settings
from app.core.rbac import Capability
from app.core.security import Principal
from app.models.enums import EvidenceType, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.audit import AuditEntryRead
from app.schemas.case import CaseCreate, CaseDetail, CaseRead
from app.schemas.evidence import EvidenceItemRead, LegalFlags
from app.schemas.graph import GraphView
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.report import ReportRead
from app.schemas.timeline import TimelineEvent
from app.schemas.user import CaseMemberCreate, CaseMemberRead, CaseMemberUpdate
from app.services.case_service import CaseService
from app.services.evidence_service import EvidenceService
from app.services.graph_query_service import GraphQueryService
from app.services.observation_service import ObservationService
from app.services.relationship_service import RelationshipService
from app.services.report_service import ReportService
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/cases", tags=["cases"])

_READ = Capability.READ_CASE_MATERIAL


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload into memory, refusing anything over ``max_bytes`` (no partial store)."""
    from app.services.errors import ValidationError

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValidationError(
                f"File exceeds the maximum upload size of {max_bytes} bytes."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _evidence_type(value: str | None) -> EvidenceType | None:
    if value is None or value == "":
        return None
    from app.services.errors import ValidationError

    try:
        return EvidenceType(value)
    except ValueError as exc:
        raise ValidationError(f"Unknown evidence_type '{value}'.") from exc


@router.get("", response_model=list[CaseRead], summary="List cases the caller may access")
def list_cases(
    principal: Principal = Depends(require(_READ)), uow: UnitOfWork = Depends(get_uow)
) -> list[CaseRead]:
    return CaseService(uow).list(principal)


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED, summary="Create a case")
def create_case(
    payload: CaseCreate,
    principal: Principal = Depends(require(Capability.CREATE_CASE)),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseRead:
    return CaseService(uow).create(payload, principal)


@router.get("/{case_id}", response_model=CaseDetail, summary="Case overview with counts")
def get_case(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseDetail:
    return CaseService(uow).detail(case_id)


@router.get("/{case_id}/observations", response_model=list[ObservationRead], summary="Observations in a case")
def case_observations(
    case_id: UUID,
    status_filter: ReviewStatus | None = Query(None, alias="status"),
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ObservationRead]:
    CaseService(uow).get(case_id)
    return ObservationService(uow).list(case_id=case_id, status=status_filter, limit=1000)


@router.get(
    "/{case_id}/relationships",
    response_model=list[RelationshipRead],
    summary="Relationships in a case",
)
def case_relationships(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> list[RelationshipRead]:
    CaseService(uow).get(case_id)
    return RelationshipService(uow).list(case_id=case_id, limit=1000)


@router.get("/{case_id}/evidence", response_model=list[EvidenceItemRead], summary="Evidence items in a case")
def case_evidence(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> list[EvidenceItemRead]:
    return EvidenceService(uow).list_for_case(case_id)


@router.post(
    "/{case_id}/evidence/upload",
    response_model=EvidenceItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a lawful evidence file (multipart); hashed and case-scoped",
)
async def upload_evidence(
    case_id: UUID,
    file: UploadFile = File(..., description="The lawful evidence file to store."),
    source_id: UUID = Form(...),
    title: str = Form(..., min_length=1),
    acknowledged: bool = Form(False, description="Safety boundaries acknowledged."),
    evidence_type: str | None = Form(None),
    description: str | None = Form(None),
    observation_id: UUID | None = Form(None),
    lawful_basis: str | None = Form(None),
    requires_legal_review: bool = Form(False),
    sensitive: bool = Form(False),
    partner_approved: bool = Form(False),
    handling_notes: str | None = Form(None),
    principal: Principal = Depends(require(Capability.CREATE_EVIDENCE)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceItemRead:
    data = await _read_capped(file, get_settings().evidence_max_upload_bytes)
    legal_flags = LegalFlags(
        lawful_basis=lawful_basis,
        requires_legal_review=requires_legal_review,
        sensitive=sensitive,
        partner_approved=partner_approved,
    )
    return EvidenceService(uow).create_from_upload(
        case_id,
        principal,
        filename=file.filename or "upload.bin",
        declared_mime=file.content_type,
        data=data,
        title=title,
        description=description,
        source_id=source_id,
        observation_id=observation_id,
        evidence_type=_evidence_type(evidence_type),
        legal_flags=legal_flags,
        handling_notes=handling_notes,
        acknowledged=acknowledged,
    )


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent], summary="Case timeline")
def case_timeline(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> list[TimelineEvent]:
    CaseService(uow).get(case_id)
    return TimelineService(uow).for_case(case_id)


@router.get(
    "/{case_id}/graph",
    response_model=GraphView,
    summary="Relationship subgraph for a case (approved relationships only)",
)
def case_graph(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> GraphView:
    return GraphQueryService(uow).case_subgraph(case_id)


@router.get("/{case_id}/audit", response_model=list[AuditEntryRead], summary="Case audit log")
def case_audit(
    case_id: UUID,
    _: Principal = Depends(require_case_audit_access),
    uow: UnitOfWork = Depends(get_uow),
) -> list[AuditEntryRead]:
    entries = CaseService(uow).audit(case_id)
    return [AuditEntryRead.model_validate(e) for e in entries]


@router.get("/{case_id}/reports", response_model=list[ReportRead], summary="Report drafts for a case")
def case_reports(
    case_id: UUID,
    _: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReportRead]:
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
    principal: Principal = Depends(require(Capability.GENERATE_REPORT)),
    uow: UnitOfWork = Depends(get_uow),
) -> ReportRead:
    return ReportService(uow).generate_draft(case_id, principal)


@router.get("/{case_id}/members", response_model=list[CaseMemberRead], summary="List case members")
def case_members(
    case_id: UUID,
    _: Principal = Depends(require_case_access),
    uow: UnitOfWork = Depends(get_uow),
) -> list[CaseMemberRead]:
    return CaseService(uow).list_members(case_id)


@router.post(
    "/{case_id}/members",
    response_model=CaseMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a case",
)
def assign_member(
    case_id: UUID,
    payload: CaseMemberCreate,
    principal: Principal = Depends(require_case_membership_management),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseMemberRead:
    return CaseService(uow).assign_member(case_id, payload, principal)


@router.patch(
    "/{case_id}/members/{membership_id}",
    response_model=CaseMemberRead,
    summary="Change a member's case role or status",
)
def update_member(
    case_id: UUID,
    membership_id: UUID,
    payload: CaseMemberUpdate,
    principal: Principal = Depends(require_case_membership_management),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseMemberRead:
    return CaseService(uow).update_member(case_id, membership_id, payload, principal)


@router.delete(
    "/{case_id}/members/{membership_id}",
    response_model=CaseMemberRead,
    summary="Remove (revoke) a member's access to a case",
)
def remove_member(
    case_id: UUID,
    membership_id: UUID,
    principal: Principal = Depends(require_case_membership_management),
    uow: UnitOfWork = Depends(get_uow),
) -> CaseMemberRead:
    return CaseService(uow).deactivate_member(case_id, membership_id, principal)
