"""Evidence service — the Evidence Locker and integrity layer.

Responsibilities:

* Create evidence items (metadata; optional bytes hashed with SHA-256).
* Link an evidence item to an observation — only within the same case.
* Decide an evidence item (approve / reject / needs_more_review / quarantine).
* Verify an evidence item's hash by re-hashing the stored bytes.

Every create, link, decision, and verify is written to the append-only audit log.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.config import get_settings
from app.core.content_store import sha256_hex
from app.core.rbac import Capability, CaseRole, can
from app.core.security import Principal
from app.core.upload_policy import UploadDecision, assess_upload
from app.models.enums import EvidenceStatus, EvidenceType
from app.repositories.uow import UnitOfWork
from app.schemas.evidence import (
    EvidenceDecision,
    EvidenceItemCreate,
    EvidenceItemRead,
    EvidenceVerifyResult,
    LegalFlags,
)
from app.services.authz import authorize_decision
from app.services.case_access import FORBIDDEN_MESSAGE, CaseAccessService
from app.services.errors import NotFoundError, PermissionDenied, ValidationError

_DECISION_STATUS: dict[EvidenceDecision, EvidenceStatus] = {
    EvidenceDecision.APPROVE: EvidenceStatus.APPROVED,
    EvidenceDecision.REJECT: EvidenceStatus.REJECTED,
    EvidenceDecision.NEEDS_MORE_REVIEW: EvidenceStatus.NEEDS_MORE_REVIEW,
    EvidenceDecision.QUARANTINE: EvidenceStatus.QUARANTINED,
}


class EvidenceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get(self, evidence_id: UUID) -> EvidenceItemRead:
        item = self.uow.evidence.get(evidence_id)
        if item is None:
            raise NotFoundError(f"Evidence item {evidence_id} not found")
        return item

    def read(self, evidence_id: UUID, principal: Principal) -> EvidenceItemRead:
        """Fetch an evidence item, enforcing case read access (need-to-know)."""
        item = self.get(evidence_id)
        if not CaseAccessService(self.uow).can_read_material(principal, item.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        return item

    def list(
        self, *, limit: int = 50, offset: int = 0, principal: Principal | None = None
    ) -> list[EvidenceItemRead]:
        results = self.uow.evidence.list(limit=limit, offset=offset)
        if principal is None:
            return results
        scoped = CaseAccessService(self.uow).readable_case_ids(principal)
        if scoped is None:  # administrator
            return results
        return [e for e in results if e.case_id in scoped]

    def list_for_case(self, case_id: UUID) -> list[EvidenceItemRead]:
        if self.uow.cases.get(case_id) is None:
            raise NotFoundError(f"Case {case_id} not found")
        return self.uow.evidence.for_case(case_id)

    def create(self, payload: EvidenceItemCreate, principal: Principal) -> EvidenceItemRead:
        if self.uow.cases.get(payload.case_id) is None:
            raise ValidationError(f"Case {payload.case_id} does not exist")
        if not CaseAccessService(self.uow).can_mutate(principal, payload.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        if self.uow.sources.get(payload.source_id) is None:
            raise ValidationError(f"Source {payload.source_id} does not exist")
        if payload.observation_id is not None:
            self._check_same_case(payload.observation_id, payload.case_id)

        sha256, size_bytes, storage_uri, has_bytes = self._resolve_content(payload)
        now = datetime.now(UTC)
        item = EvidenceItemRead(
            id=uuid4(),
            case_id=payload.case_id,
            source_id=payload.source_id,
            observation_id=payload.observation_id,
            title=payload.title,
            description=payload.description,
            evidence_type=payload.evidence_type,
            storage_uri=storage_uri,
            original_filename=payload.original_filename,
            mime_type=payload.mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            captured_at=payload.captured_at or now,
            captured_by=payload.captured_by or principal.id,
            access_method=payload.access_method,
            legal_flags=payload.legal_flags,
            handling_notes=payload.handling_notes,
            status=EvidenceStatus.PROPOSED,
            has_bytes=has_bytes,
            created_by=principal.id,
            created_at=now,
        )
        self.uow.evidence.add(item)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="evidence.created",
                target_type="evidence",
                target_id=item.id,
                case_id=item.case_id,
                context={
                    "evidence_type": item.evidence_type.value,
                    "sha256": item.sha256,
                    "has_bytes": has_bytes,
                },
            )
        )
        return item

    def create_from_upload(
        self,
        case_id: UUID,
        principal: Principal,
        *,
        filename: str,
        declared_mime: str | None,
        data: bytes,
        title: str,
        description: str | None,
        source_id: UUID,
        observation_id: UUID | None,
        evidence_type: EvidenceType | None,
        legal_flags: LegalFlags,
        handling_notes: str | None,
        acknowledged: bool,
    ) -> EvidenceItemRead:
        """Store a manually uploaded lawful file as an evidence item (v0.7).

        Enforces the safety acknowledgement, case mutation access, and the upload policy
        (dangerous types refused; unknown types quarantined; allowed types accepted). The
        bytes are hashed and content-addressed; the hash is the integrity anchor.
        """
        if not acknowledged:
            raise ValidationError(
                "You must acknowledge the safety boundaries before uploading evidence."
            )
        if self.uow.cases.get(case_id) is None:
            raise ValidationError(f"Case {case_id} does not exist")
        if not CaseAccessService(self.uow).can_mutate(principal, case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        if self.uow.sources.get(source_id) is None:
            raise ValidationError(f"Source {source_id} does not exist")
        if observation_id is not None:
            self._check_same_case(observation_id, case_id)

        settings = get_settings()
        assessment = assess_upload(
            filename,
            declared_mime,
            allowed_mimes=settings.evidence_allowed_mime_set,
            blocked_extensions=settings.evidence_blocked_extension_set,
        )
        if assessment.decision is UploadDecision.REJECT:
            # Refused outright — bytes are never stored.
            raise ValidationError(assessment.reason)

        digest = self.uow.content.put(data)
        status = (
            EvidenceStatus.QUARANTINED
            if assessment.decision is UploadDecision.QUARANTINE
            else EvidenceStatus.PROPOSED
        )
        now = datetime.now(UTC)
        item = EvidenceItemRead(
            id=uuid4(),
            case_id=case_id,
            source_id=source_id,
            observation_id=observation_id,
            title=title,
            description=description,
            evidence_type=evidence_type or self._derive_type(assessment.effective_mime),
            storage_uri=f"orca-content://{digest}",
            original_filename=filename,
            mime_type=assessment.effective_mime,
            size_bytes=len(data),
            sha256=digest,
            captured_at=now,
            captured_by=principal.id,
            access_method="manual_upload",
            legal_flags=legal_flags,
            handling_notes=handling_notes,
            status=status,
            has_bytes=True,
            created_by=principal.id,
            created_at=now,
        )
        self.uow.evidence.add(item)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="evidence.uploaded",
                target_type="evidence",
                target_id=item.id,
                case_id=case_id,
                context={
                    "sha256": digest,
                    "size_bytes": len(data),
                    "mime_type": assessment.effective_mime,
                    "original_filename": filename,
                    "decision": assessment.decision.value,
                },
            )
        )
        if status is EvidenceStatus.QUARANTINED:
            self.uow.audit.record(
                new_audit_entry(
                    actor_id=principal.id,
                    action="evidence.quarantined",
                    target_type="evidence",
                    target_id=item.id,
                    case_id=case_id,
                    context={"reason": assessment.reason, "trigger": "upload_policy"},
                )
            )
        return item

    def download(self, evidence_id: UUID, principal: Principal) -> tuple[EvidenceItemRead, bytes]:
        """Return an evidence item and its stored bytes for an authorised caller.

        Raw bytes are restricted to administrators and mutating members (case manager /
        analyst / reviewer); viewers and partner export viewers are refused unless a
        deployment opts viewers in for approved evidence. Every download is audited."""
        item = self.get(evidence_id)
        if not self._can_download(principal, item):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        if not item.has_bytes or not item.sha256:
            raise NotFoundError("This evidence item has no stored bytes to download")
        data = self.uow.content.get(item.sha256)
        if data is None:
            raise NotFoundError("Stored bytes for this evidence item are unavailable")
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="evidence.downloaded",
                target_type="evidence",
                target_id=item.id,
                case_id=item.case_id,
                context={
                    "sha256": item.sha256,
                    "size_bytes": item.size_bytes,
                    "original_filename": item.original_filename,
                },
            )
        )
        return item, data

    def _can_download(self, principal: Principal, item: EvidenceItemRead) -> bool:
        access = CaseAccessService(self.uow)
        if access.can_access_raw_file(principal, item.case_id):
            return True
        # Policy hook: case viewers may download APPROVED bytes only if explicitly enabled.
        return (
            get_settings().evidence_allow_viewer_download
            and item.status is EvidenceStatus.APPROVED
            and access.effective_case_role(principal, item.case_id) is CaseRole.VIEWER
        )

    @staticmethod
    def _derive_type(mime: str) -> EvidenceType:
        if mime.startswith("image/"):
            return EvidenceType.IMAGE
        if mime.startswith("video/"):
            return EvidenceType.VIDEO
        if mime == "application/pdf" or mime.startswith("text/"):
            return EvidenceType.DOCUMENT
        return EvidenceType.OTHER

    def link_to_observation(
        self, evidence_id: UUID, observation_id: UUID, principal: Principal
    ) -> EvidenceItemRead:
        item = self.get(evidence_id)
        if not CaseAccessService(self.uow).can_mutate(principal, item.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        self._check_same_case(observation_id, item.case_id)
        updated = item.model_copy(update={"observation_id": observation_id})
        self.uow.evidence.replace(updated)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="evidence.linked",
                target_type="evidence",
                target_id=item.id,
                case_id=item.case_id,
                context={"observation_id": str(observation_id)},
            )
        )
        return updated

    def decide(
        self,
        evidence_id: UUID,
        decision: EvidenceDecision,
        principal: Principal,
        note: str | None = None,
        override: bool = False,
    ) -> EvidenceItemRead:
        if not can(principal.role, Capability.REVIEW_DECIDE):
            raise PermissionDenied("Deciding an evidence item requires review authority")
        item = self.get(evidence_id)
        # Need-to-know: a reviewer may only decide evidence in cases they review.
        if not CaseAccessService(self.uow).can_review(principal, item.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        # Separation of duties: no self-review without an admin override.
        is_override = authorize_decision(principal, item.created_by, override)
        new_status = _DECISION_STATUS[decision]
        updated = item.model_copy(update={"status": new_status})
        self.uow.evidence.replace(updated)
        action = "evidence.override" if is_override else f"evidence.{decision.value}"
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type="evidence",
                target_id=item.id,
                case_id=item.case_id,
                context={
                    "decision": decision.value,
                    "resulting_status": new_status.value,
                    "override": is_override,
                    "proposer": item.created_by,
                    "note": note,
                },
            )
        )
        return updated

    def verify(self, evidence_id: UUID, principal: Principal) -> EvidenceVerifyResult:
        item = self.get(evidence_id)
        if not CaseAccessService(self.uow).can_read_material(principal, item.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        recorded = item.sha256
        computed: str | None = None
        verified: bool | None = None

        if recorded and self.uow.content.exists(recorded):
            data = self.uow.content.get(recorded)
            computed = sha256_hex(data) if data is not None else None
            verified = computed == recorded
            message = "Hash verified against stored bytes." if verified else "INTEGRITY MISMATCH."
        elif recorded:
            message = "Recorded hash present, but ORCA holds no bytes to re-verify."
        else:
            message = "No hash recorded for this evidence item."

        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="evidence.verified",
                target_type="evidence",
                target_id=item.id,
                case_id=item.case_id,
                context={"verified": verified, "recorded_sha256": recorded, "computed_sha256": computed},
            )
        )
        return EvidenceVerifyResult(
            evidence_id=item.id,
            has_bytes=item.has_bytes,
            recorded_sha256=recorded,
            computed_sha256=computed,
            verified=verified,
            message=message,
        )

    # --- helpers -----------------------------------------------------------------

    def _check_same_case(self, observation_id: UUID, case_id: UUID) -> None:
        observation = self.uow.observations.get(observation_id)
        if observation is None:
            raise ValidationError(f"Observation {observation_id} does not exist")
        if observation.case_id != case_id:
            raise ValidationError(
                "Evidence cannot be linked across unrelated cases: the observation belongs to a "
                "different case."
            )

    def _resolve_content(
        self, payload: EvidenceItemCreate
    ) -> tuple[str | None, int | None, str | None, bool]:
        if payload.content_text is not None and payload.content_base64 is not None:
            raise ValidationError("Provide at most one of 'content_text' or 'content_base64'.")

        data: bytes | None = None
        if payload.content_text is not None:
            data = payload.content_text.encode("utf-8")
        elif payload.content_base64 is not None:
            try:
                data = base64.b64decode(payload.content_base64, validate=True)
            except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
                raise ValidationError("content_base64 is not valid base64.") from exc

        if data is not None:
            digest = self.uow.content.put(data)
            storage_uri = payload.storage_uri or f"orca-content://{digest}"
            return digest, len(data), storage_uri, True

        # No bytes available: keep any partner-provided hash / external reference.
        return payload.sha256, payload.size_bytes, payload.storage_uri, False
