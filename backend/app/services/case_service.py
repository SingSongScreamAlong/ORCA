"""Case service.

A case is a curated view over evidence; it does not own observations or relationships.
The service provides creation, listing (scoped to the caller's case memberships),
an overview with aggregate counts, the case-scoped audit log, and the case membership
roster + lifecycle (v0.6).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import AuditEntry, new_audit_entry
from app.core.rbac import CaseRole, MembershipStatus, default_case_role
from app.core.security import Principal
from app.models.enums import CaseStatus, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.case import CaseCounts, CaseCreate, CaseDetail, CaseRead
from app.schemas.user import CaseMemberCreate, CaseMemberRead, CaseMemberUpdate
from app.services.case_access import CaseAccessService
from app.services.errors import NotFoundError, ValidationError


class CaseService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.access = CaseAccessService(uow)

    def list(self, principal: Principal, *, limit: int = 50, offset: int = 0) -> list[CaseRead]:
        """List cases the principal may access — all for admins, assigned only otherwise."""
        cases = self.uow.cases.list(limit=limit, offset=offset)
        accessible = self.access.accessible_case_ids(principal)
        if accessible is None:  # administrator
            return cases
        return [c for c in cases if c.id in accessible]

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
        # The creator becomes the case's manager so they can work it immediately and
        # enrol others. (Administrators access every case regardless, but recording the
        # membership keeps the roster honest.)
        self._grant(
            case_id=case.id,
            user=self.uow.users.get(UUID(principal.id)),
            case_role=CaseRole.CASE_MANAGER,
            principal=principal,
            now=now,
            note="case creator",
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

    # --- membership roster + lifecycle ------------------------------------------

    def list_members(self, case_id: UUID) -> list[CaseMemberRead]:
        self.get(case_id)
        return self.uow.memberships.for_case(case_id)

    def assign_member(
        self, case_id: UUID, payload: CaseMemberCreate, principal: Principal
    ) -> CaseMemberRead:
        self.get(case_id)
        user = self.uow.users.get_by_username(payload.username)
        if user is None:
            raise ValidationError(f"User '{payload.username}' does not exist")

        case_role = payload.case_role or default_case_role(user.role)
        existing = self.uow.memberships.find(case_id, user.id)
        if existing is not None and existing.status == MembershipStatus.ACTIVE:
            raise ValidationError(f"User '{payload.username}' is already an active member of this case")

        now = datetime.now(UTC)
        if existing is not None:
            # Reactivate a previously removed membership in place (keeps it unique).
            old_status = existing.status
            updated = existing.model_copy(
                update={
                    "case_role": case_role,
                    "status": MembershipStatus.ACTIVE,
                    "assigned_by": principal.username,
                    "assigned_at": now,
                    "notes": payload.notes,
                    "updated_at": now,
                }
            )
            self.uow.memberships.replace(updated)
            self._audit_membership(
                principal, case_id, updated, "case.member_reactivated",
                extra={"old_status": old_status.value},
            )
            return updated

        member = self._grant(
            case_id=case_id, user=user, case_role=case_role,
            principal=principal, now=now, note=payload.notes,
        )
        return member

    def update_member(
        self, case_id: UUID, membership_id: UUID, payload: CaseMemberUpdate, principal: Principal
    ) -> CaseMemberRead:
        member = self._member_in_case(case_id, membership_id)
        now = datetime.now(UTC)
        new_role = payload.case_role or member.case_role
        new_status = payload.status or member.status
        new_notes = payload.notes if payload.notes is not None else member.notes
        updated = member.model_copy(
            update={
                "case_role": new_role, "status": new_status, "notes": new_notes,
                "assigned_by": principal.username, "assigned_at": now, "updated_at": now,
            }
        )
        self.uow.memberships.replace(updated)

        if payload.case_role is not None and payload.case_role != member.case_role:
            self._audit_membership(
                principal, case_id, updated, "case.member_role_changed",
                extra={"old_case_role": member.case_role.value},
            )
        if payload.status is not None and payload.status != member.status:
            self._audit_membership(
                principal, case_id, updated, "case.member_status_changed",
                extra={"old_status": member.status.value},
            )
        return updated

    def deactivate_member(
        self, case_id: UUID, membership_id: UUID, principal: Principal
    ) -> CaseMemberRead:
        member = self._member_in_case(case_id, membership_id)
        now = datetime.now(UTC)
        old_status = member.status
        updated = member.model_copy(
            update={
                "status": MembershipStatus.REVOKED,
                "assigned_by": principal.username,
                "assigned_at": now,
                "updated_at": now,
            }
        )
        self.uow.memberships.replace(updated)
        self._audit_membership(
            principal, case_id, updated, "case.member_deactivated",
            extra={"old_status": old_status.value},
        )
        return updated

    # --- helpers -----------------------------------------------------------------

    def _member_in_case(self, case_id: UUID, membership_id: UUID) -> CaseMemberRead:
        self.get(case_id)
        member = self.uow.memberships.get(membership_id)
        if member is None or member.case_id != case_id:
            raise NotFoundError(f"Membership {membership_id} not found in case {case_id}")
        return member

    def _grant(
        self, *, case_id: UUID, user, case_role: CaseRole, principal: Principal,
        now: datetime, note: str | None,
    ) -> CaseMemberRead:
        if user is None:
            raise ValidationError("Cannot assign a membership for an unknown user")
        member = CaseMemberRead(
            id=uuid4(), case_id=case_id, user_id=user.id, username=user.username,
            display_name=user.display_name, global_role=user.role, case_role=case_role,
            status=MembershipStatus.ACTIVE, assigned_by=principal.username, assigned_at=now,
            notes=note, created_at=now, updated_at=now,
        )
        self.uow.memberships.add(member)
        self._audit_membership(principal, case_id, member, "case.member_added")
        return member

    def _audit_membership(
        self, principal: Principal, case_id: UUID, member: CaseMemberRead, action: str,
        extra: dict | None = None,
    ) -> None:
        context = {
            "membership_id": str(member.id),
            "target_user_id": str(member.user_id),
            "target_username": member.username,
            "target_case_role": member.case_role.value,
            "status": member.status.value,
        }
        if extra:
            context.update(extra)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type="case_membership",
                target_id=member.id,
                case_id=case_id,
                context=context,
            )
        )
