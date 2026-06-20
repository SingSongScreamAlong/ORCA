"""Analyst Copilot endpoints (v1.0) — propose-only AI assistance.

Every endpoint is case-membership gated (``require_case_material_read``): partner export
viewers lack ``read_case_material`` and so cannot reach the Copilot, and unassigned users
get a generic 403. Results are always proposed-only and require human review; the Copilot
never writes case material. See ``docs/v1.0_aip_assisted_analyst_copilot.md``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends

from app.ai_assist.models import AiAssistRequest, AiAssistResult
from app.ai_assist.service import AiAssistService
from app.api.deps import get_uow, require_case_material_read
from app.core.security import Principal
from app.repositories.uow import UnitOfWork

router = APIRouter(prefix="/cases", tags=["ai-copilot"])

_EMPTY = AiAssistRequest()


@router.post(
    "/{case_id}/ai/summarize",
    response_model=AiAssistResult,
    summary="Summarize approved case material",
)
def summarize(
    case_id: UUID,
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).summarize(case_id, principal)


@router.post(
    "/{case_id}/ai/extract-entities",
    response_model=AiAssistResult,
    summary="Extract candidate entities (proposed only)",
)
def extract_entities(
    case_id: UUID,
    payload: AiAssistRequest = Body(default=_EMPTY),
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).extract_entities(case_id, principal, payload.note)


@router.post(
    "/{case_id}/ai/suggest-relationships",
    response_model=AiAssistResult,
    summary="Suggest relationship candidates (proposed only)",
)
def suggest_relationships(
    case_id: UUID,
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).suggest_relationships(case_id, principal)


@router.post(
    "/{case_id}/ai/draft-report-section",
    response_model=AiAssistResult,
    summary="Draft a report section from approved observations (proposed only)",
)
def draft_report_section(
    case_id: UUID,
    payload: AiAssistRequest = Body(default=_EMPTY),
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).draft_report_section(case_id, principal, payload.section_title)


@router.post(
    "/{case_id}/ai/check-citations",
    response_model=AiAssistResult,
    summary="Flag missing citations / unsupported claims in a draft",
)
def check_citations(
    case_id: UUID,
    payload: AiAssistRequest = Body(default=_EMPTY),
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).check_citations(case_id, principal, payload.draft_text)


@router.post(
    "/{case_id}/ai/timeline-summary",
    response_model=AiAssistResult,
    summary="Summarize the approved case timeline",
)
def timeline_summary(
    case_id: UUID,
    principal: Principal = Depends(require_case_material_read),
    uow: UnitOfWork = Depends(get_uow),
) -> AiAssistResult:
    return AiAssistService(uow).timeline_summary(case_id, principal)
