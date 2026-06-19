"""Case service.

A case is a curated view over evidence; it does not own observations or relationships.
The service provides creation, listing, an overview with aggregate counts, and the
case-scoped audit log.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import AuditEntry, new_audit_entry
from app.core.security import Principal
from app.models.enums import CaseStatus, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.case import CaseCounts, CaseCreate, CaseDetail, CaseRead
from app.schemas.user import CaseMemberRead
from app.services.errors import NotFoundError, ValidationError


class CaseService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(self, *, limit: int = 50, offset: int = 0) -> list[CaseRead]:
        return self.uow.cases.list(limit=limit, offset=offset)

    def get(self, case_id: UUID) -> CaseRead:
        case = self.uow.cases.get(case_id)
        if case is None:
            raise NotFoundError(f"Case {case_id} not found")
        return case

    def create(self, payload: CaseCreate, principal: Principal) -> CaseRead:
        now = datetime.now(UTC)
        case = CaseRead(
            id=uuid4(),
            title=payload.title,
            status=CaseStatus.OPEN,
            owner=payload.owner or principal.id,
            summary=payload.summary,
            legal_notes=payload.legal_notes,
            created_at=now,
            updated_at=now,
        )
        self.uow.cases.add(case)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="case.created",
                target_type="case",
                target_id=case.id,
                case_id=case.id,
                context={"title": case.title},
            )
        )
        return case

    def detail(self, case_id: UUID) -> CaseDetail:
        case = self.get(case_id)
        observations = self.uow.observations.for_case(case_id)
        relationships = self.uow.relationships.for_case(case_id)
        counts = CaseCounts(
            observations_total=len(observations),
            observations_approved=sum(1 for o in observations if o.status == ReviewStatus.APPROVED),
            observations_pending=sum(1 for o in observations if o.status == ReviewStatus.PROPOSED),
            relationships=len(relationships),
        )
        return CaseDetail(case=case, counts=counts)

    def audit(self, case_id: UUID) -> list[AuditEntry]:
        self.get(case_id)  # 404 if missing
        return self.uow.audit.list(case_id=case_id)

    def list_members(self, case_id: UUID) -> list[CaseMemberRead]:
        self.get(case_id)
        return self.uow.memberships.for_case(case_id)

    def assign_member(self, case_id: UUID, username: str, principal: Principal) -> CaseMemberRead:
        self.get(case_id)
        user = self.uow.users.get_by_username(username)
        if user is None:
            raise ValidationError(f"User '{username}' does not exist")
        if self.uow.memberships.exists(case_id, user.id):
            raise ValidationError(f"User '{username}' is already assigned to this case")
        member = CaseMemberRead(
            id=uuid4(), case_id=case_id, user_id=user.id, username=user.username, role=user.role,
            assigned_by=principal.username, assigned_at=datetime.now(UTC),
        )
        self.uow.memberships.add(member)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="case.member_assigned",
                target_type="case",
                target_id=case_id,
                case_id=case_id,
                context={"assigned_user": user.username, "role": user.role.value},
            )
        )
        return member
