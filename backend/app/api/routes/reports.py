"""Report endpoints.

Reports are generated under a case (see the cases router). Here we expose published
("approved") report packages, single-report access, and publishing.

Partner export viewers may ONLY access published reports — never raw case material.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import current_principal, get_uow, require
from app.core.rbac import Capability, can
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.report import ReportRead
from app.services.case_access import FORBIDDEN_MESSAGE, CaseAccessService
from app.services.errors import PermissionDenied
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/published",
    response_model=list[ReportRead],
    summary="List published (approved) report packages for the caller's cases",
)
def list_published(
    principal: Principal = Depends(require(Capability.VIEW_APPROVED_REPORTS)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReportRead]:
    return ReportService(uow).list_published(principal)


@router.get("/{report_id}", response_model=ReportRead, summary="Get a report")
def get_report(
    report_id: UUID,
    principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> ReportRead:
    report = ReportService(uow).get(report_id)
    access = CaseAccessService(uow)
    # Members who may read raw material see any status (drafts included).
    if can(principal.role, Capability.READ_CASE_MATERIAL) and access.can_read_material(
        principal, report.case_id
    ):
        return report
    # Otherwise only a published package, and only for a case the caller is assigned to
    # (this is the partner export viewer's only window into a case).
    if (
        can(principal.role, Capability.VIEW_APPROVED_REPORTS)
        and report.status == "final"
        and access.can_view_reports(principal, report.case_id)
    ):
        return report
    raise PermissionDenied(FORBIDDEN_MESSAGE)


@router.post("/{report_id}/publish", response_model=ReportRead, summary="Publish a report (mark final)")
def publish_report(
    report_id: UUID,
    principal: Principal = Depends(require(Capability.PUBLISH_REPORT)),
    uow: UnitOfWork = Depends(get_uow),
) -> ReportRead:
    return ReportService(uow).publish(report_id, principal)
