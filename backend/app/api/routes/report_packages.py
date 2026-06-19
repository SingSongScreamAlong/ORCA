"""Report package endpoints (v0.8 — partner-ready export).

Listing and download require ``VIEW_APPROVED_REPORTS`` and are scoped to the caller's
case memberships (administrators see all). A ``partner_export_viewer`` reaches packages
for assigned cases here, but never raw evidence, the graph, the audit log, or unapproved
material — those endpoints require ``READ_CASE_MATERIAL``, which partners lack.
Generation lives on the cases router (``POST /cases/{id}/report/package``).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_uow, require
from app.core.rbac import Capability
from app.core.security import Principal
from app.repositories.uow import UnitOfWork
from app.schemas.report_package import ReportPackageSummary
from app.services.report_package_service import ReportPackageService

router = APIRouter(prefix="/report-packages", tags=["report-packages"])

_VIEW = Capability.VIEW_APPROVED_REPORTS


@router.get(
    "",
    response_model=list[ReportPackageSummary],
    summary="List report packages for the caller's cases",
)
def list_packages(
    principal: Principal = Depends(require(_VIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> list[ReportPackageSummary]:
    return ReportPackageService(uow).list_for_principal(principal)


@router.get("/{package_id}", response_model=ReportPackageSummary, summary="Report package metadata")
def get_package(
    package_id: UUID,
    principal: Principal = Depends(require(_VIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> ReportPackageSummary:
    return ReportPackageService(uow).get(package_id, principal)


@router.get("/{package_id}/report", summary="Download the package report (Markdown)", response_class=Response)
def download_report(
    package_id: UUID,
    principal: Principal = Depends(require(_VIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> Response:
    package, text = ReportPackageService(uow).report_markdown(package_id, principal)
    return Response(
        content=text,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="report-{package.id}.md"'},
    )


@router.get(
    "/{package_id}/manifest",
    summary="Download the evidence manifest (JSON)",
    response_class=Response,
)
def download_manifest(
    package_id: UUID,
    principal: Principal = Depends(require(_VIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> Response:
    package, text = ReportPackageService(uow).manifest_json(package_id, principal)
    return Response(
        content=text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="manifest-{package.id}.json"'},
    )


@router.get("/{package_id}/package", summary="Download the full package (ZIP)", response_class=Response)
def download_package(
    package_id: UUID,
    principal: Principal = Depends(require(_VIEW)),
    uow: UnitOfWork = Depends(get_uow),
) -> Response:
    package, data = ReportPackageService(uow).zip_bytes(package_id, principal)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="report-package-{package.id}.zip"'},
    )
