"""Report read endpoints. Reports are generated under a case (see the cases router)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_uow
from app.repositories.uow import UnitOfWork
from app.schemas.report import ReportRead
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}", response_model=ReportRead, summary="Get a report")
def get_report(report_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> ReportRead:
    return ReportService(uow).get(report_id)
