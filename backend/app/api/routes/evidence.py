"""Evidence Locker endpoints (v0.3+), guarded by RBAC (v0.4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Pagination, get_uow, pagination, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.evidence import (
    EvidenceDecisionRequest,
    EvidenceItemCreate,
    EvidenceItemRead,
    EvidenceLinkRequest,
    EvidenceVerifyResult,
)
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("", response_model=list[EvidenceItemRead], summary="List evidence items")
def list_evidence(
    page: Pagination = Depends(pagination),
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[EvidenceItemRead]:
    return EvidenceService(uow).list(limit=page.limit, offset=page.offset, principal=principal)


@router.post(
    "",
    response_model=EvidenceItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an evidence item (hashes bytes if provided)",
)
def create_evidence(
    payload: EvidenceItemCreate,
    principal: Principal = Depends(require(Capability.CREATE_EVIDENCE)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceItemRead:
    return EvidenceService(uow).create(payload, principal)


@router.get("/{evidence_id}", response_model=EvidenceItemRead, summary="Get an evidence item")
def get_evidence(
    evidence_id: UUID,
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceItemRead:
    return EvidenceService(uow).read(evidence_id, principal)


@router.post(
    "/{evidence_id}/link",
    response_model=EvidenceItemRead,
    summary="Link an evidence item to an observation (same case only)",
)
def link_evidence(
    evidence_id: UUID,
    request: EvidenceLinkRequest,
    principal: Principal = Depends(require(Capability.CREATE_EVIDENCE)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceItemRead:
    return EvidenceService(uow).link_to_observation(evidence_id, request.observation_id, principal)


@router.post(
    "/{evidence_id}/decision",
    response_model=EvidenceItemRead,
    summary="Decide an evidence item (approve / reject / needs_more_review / quarantine)",
)
def decide_evidence(
    evidence_id: UUID,
    request: EvidenceDecisionRequest,
    principal: Principal = Depends(require(Capability.REVIEW_DECIDE)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceItemRead:
    return EvidenceService(uow).decide(
        evidence_id, request.decision, principal, note=request.note, override=request.override
    )


@router.post(
    "/{evidence_id}/verify",
    response_model=EvidenceVerifyResult,
    summary="Verify an evidence item's SHA-256 against the stored bytes",
)
def verify_evidence(
    evidence_id: UUID,
    principal: Principal = Depends(require(Capability.READ_CASE_MATERIAL)),
    uow: UnitOfWork = Depends(get_uow),
) -> EvidenceVerifyResult:
    return EvidenceService(uow).verify(evidence_id, principal)
