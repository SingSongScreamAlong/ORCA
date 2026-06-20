"""Analyst Copilot service (v1.0) — propose-only AI assistance.

Gathers a case's **approved** material, asks the configured provider for suggestions, and
returns them wrapped as explicitly *proposed* results that require human review. The
Copilot never writes case material, never approves anything, and is gated by case
membership (partner export viewers and unassigned users cannot reach it). Every request is
audited. See ``docs/v1.0_aip_assisted_analyst_copilot.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.ai_assist.models import AiAssistResult, AiMeta, AiSuggestion
from app.ai_assist.provider import CopilotContext, build_provider
from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import EvidenceStatus, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.services.case_access import FORBIDDEN_MESSAGE, CaseAccessService
from app.services.errors import NotFoundError, PermissionDenied
from app.services.timeline_service import TimelineService


class AiAssistService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.access = CaseAccessService(uow)
        self.provider = build_provider()

    # --- guards / context --------------------------------------------------------

    def _require_read(self, principal: Principal, case_id: UUID) -> None:
        if self.uow.cases.get(case_id) is None:
            raise NotFoundError(f"Case {case_id} not found")
        if not self.access.can_read_material(principal, case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)

    def _context(self, case_id: UUID) -> CopilotContext:
        """Approved material only — the Copilot never reasons over unapproved material."""
        case = self.uow.cases.get(case_id)
        observations = [
            o for o in self.uow.observations.for_case(case_id) if o.status is ReviewStatus.APPROVED
        ]
        approved_ids = {o.id for o in observations}
        relationships = [
            r
            for r in self.uow.relationships.for_case(case_id)
            if r.status is ReviewStatus.APPROVED
            and all(oid in approved_ids for oid in r.observation_ids)
        ]
        evidence = [
            e for e in self.uow.evidence.for_case(case_id) if e.status is EvidenceStatus.APPROVED
        ]
        entities: dict = {}
        wanted: set[UUID] = set()
        for o in observations:
            wanted.update(o.entity_ids)
        for r in relationships:
            wanted.update({r.source_entity_id, r.target_entity_id})
        for eid in wanted:
            entity = self.uow.entities.get(eid)
            if entity is not None:
                entities[eid] = entity
        timeline = TimelineService(self.uow).for_case(case_id)
        return CopilotContext(
            case_title=case.title,
            observations=observations,
            relationships=relationships,
            evidence=evidence,
            entities=entities,
            timeline=timeline,
        )

    def _meta(self, source_ids: list[str]) -> AiMeta:
        return AiMeta(
            provider=self.provider.name,
            generated_at=datetime.now(UTC),
            source_material_ids=source_ids,
        )

    def _audit(self, principal: Principal, case_id: UUID, assist_type: str, context: dict) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=f"ai_assist.{assist_type}",
                target_type="ai_assist",
                target_id=case_id,
                case_id=case_id,
                context={"provider": self.provider.name, **context},
            )
        )

    # --- endpoints ---------------------------------------------------------------

    def summarize(self, case_id: UUID, principal: Principal) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        summary, suggestions = self.provider.summarize(ctx)
        self._audit(principal, case_id, "summarize", {"observations": len(ctx.observations)})
        return AiAssistResult(
            case_id=case_id, assist_type="summarize",
            meta=self._meta([str(o.id) for o in ctx.observations]),
            summary=summary, suggestions=suggestions,
        )

    def extract_entities(self, case_id: UUID, principal: Principal, note: str | None) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        texts: list[tuple[str, str]] = []
        if note:
            texts.append(("", note))
        texts.extend((str(o.id), o.notes) for o in ctx.observations if o.notes)
        proposed = self.provider.extract_entities(ctx, texts)
        suggestions = [
            AiSuggestion(
                kind="duplicate_entity",
                text=f"Candidate '{p.value}' may duplicate an existing entity.",
                rationale=f"Matches existing entity {p.possible_duplicate_of}.",
            )
            for p in proposed
            if p.possible_duplicate_of
        ]
        self._audit(principal, case_id, "extract_entities", {"proposed_entities": len(proposed)})
        return AiAssistResult(
            case_id=case_id, assist_type="extract_entities",
            meta=self._meta([str(o.id) for o in ctx.observations]),
            proposed_entities=proposed, suggestions=suggestions,
        )

    def suggest_relationships(self, case_id: UUID, principal: Principal) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        proposed = self.provider.suggest_relationships(ctx)
        self._audit(principal, case_id, "suggest_relationships", {"proposed": len(proposed)})
        return AiAssistResult(
            case_id=case_id, assist_type="suggest_relationships",
            meta=self._meta([str(o.id) for o in ctx.observations]),
            proposed_relationships=proposed,
        )

    def draft_report_section(
        self, case_id: UUID, principal: Principal, section_title: str | None
    ) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        draft = self.provider.draft_report_section(ctx, section_title or "Findings")
        self._audit(principal, case_id, "draft_report_section", {"section": draft.section_title})
        return AiAssistResult(
            case_id=case_id, assist_type="draft_report_section",
            meta=self._meta(list(draft.cited_observation_ids)),
            report_draft=draft,
        )

    def check_citations(
        self, case_id: UUID, principal: Principal, draft_text: str | None
    ) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        gaps, unsupported = self.provider.check_citations(ctx, draft_text or "")
        self._audit(
            principal, case_id, "check_citations",
            {"gaps": len(gaps), "unsupported": len(unsupported)},
        )
        return AiAssistResult(
            case_id=case_id, assist_type="check_citations",
            meta=self._meta([str(o.id) for o in ctx.observations]),
            citation_gaps=gaps, unsupported_claims=unsupported,
        )

    def timeline_summary(self, case_id: UUID, principal: Principal) -> AiAssistResult:
        self._require_read(principal, case_id)
        ctx = self._context(case_id)
        summary = self.provider.timeline_summary(ctx)
        self._audit(principal, case_id, "timeline_summary", {"events": len(ctx.timeline)})
        return AiAssistResult(
            case_id=case_id, assist_type="timeline_summary",
            meta=self._meta([str(o.id) for o in ctx.observations]),
            summary=summary,
        )
