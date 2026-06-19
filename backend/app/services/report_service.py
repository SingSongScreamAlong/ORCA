"""Report service.

Generates a draft report from a case using ONLY approved evidence. Proposed and
rejected observations are excluded by construction. The draft is persisted with
``status = draft`` and the action is audited.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import EvidenceStatus, ReportStatus, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.report import ReportRead
from app.services.errors import NotFoundError


class ReportService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def list(self, case_id: UUID) -> list[ReportRead]:
        return self.uow.reports.list(case_id=case_id)

    def list_published(self) -> list[ReportRead]:
        return self.uow.reports.list_published()

    def get(self, report_id: UUID) -> ReportRead:
        report = self.uow.reports.get(report_id)
        if report is None:
            raise NotFoundError(f"Report {report_id} not found")
        return report

    def publish(self, report_id: UUID, principal: Principal) -> ReportRead:
        """Mark a draft report as final — an approved report package."""
        report = self.get(report_id)
        updated = report.model_copy(
            update={"status": ReportStatus.FINAL, "updated_at": datetime.now(UTC)}
        )
        self.uow.reports.replace(updated)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="report.published",
                target_type="report",
                target_id=report.id,
                case_id=report.case_id,
                context={"title": report.title},
            )
        )
        return updated

    def generate_draft(self, case_id: UUID, principal: Principal) -> ReportRead:
        case = self.uow.cases.get(case_id)
        if case is None:
            raise NotFoundError(f"Case {case_id} not found")

        approved_observations = [
            o for o in self.uow.observations.for_case(case_id) if o.status is ReviewStatus.APPROVED
        ]
        approved_observation_ids = {o.id for o in approved_observations}
        relationships = [
            r
            for r in self.uow.relationships.for_case(case_id)
            if r.status is ReviewStatus.APPROVED
            and all(oid in approved_observation_ids for oid in r.observation_ids)
        ]

        now = datetime.now(UTC)
        body = self._render(case, approved_observations, relationships, now)
        report = ReportRead(
            id=uuid4(),
            case_id=case_id,
            title=f"Draft report — {case.title}",
            author=principal.id,
            status=ReportStatus.DRAFT,
            body=body,
            created_at=now,
            updated_at=now,
        )
        self.uow.reports.add(report)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="report.generated",
                target_type="report",
                target_id=report.id,
                case_id=case_id,
                context={
                    "approved_observations": len(approved_observations),
                    "relationships": len(relationships),
                },
            )
        )
        return report

    def _render(self, case, observations, relationships, generated_at: datetime) -> str:
        def entity_label(entity_id: UUID) -> str:
            entity = self.uow.entities.get(entity_id)
            return f"{entity.entity_type.value}:{entity.value}" if entity else str(entity_id)[:8]

        lines: list[str] = []
        lines.append(f"# Draft report — {case.title}")
        lines.append("")
        lines.append(
            f"_Generated {generated_at.isoformat(timespec='seconds')} by {case.owner}. "
            "Status: draft._"
        )
        lines.append("")
        lines.append(
            "> This draft uses only **approved** evidence. Proposed and rejected "
            "observations are excluded. All conclusions remain analyst-reviewed."
        )
        lines.append("")
        lines.append("## Case")
        lines.append(f"- **Status:** {case.status.value}")
        lines.append(f"- **Owner:** {case.owner}")
        if case.summary:
            lines.append(f"- **Summary:** {case.summary}")
        if case.legal_notes:
            lines.append(f"- **Legal / handling:** {case.legal_notes}")
        lines.append("")

        cited_evidence = 0
        lines.append(f"## Approved observations ({len(observations)})")
        if not observations:
            lines.append("_No approved observations yet._")
        for o in sorted(observations, key=lambda x: x.timestamp):
            source = self.uow.sources.get(o.source_id)
            source_name = source.name if source else str(o.source_id)[:8]
            lines.append(
                f"- `{str(o.id)[:8]}` {o.timestamp.date()} — {o.notes or '(no notes)'} "
                f"(source: {source_name}; confidence {o.confidence:.0%})"
            )
            # Cite only APPROVED evidence linked to this observation (excludes
            # proposed / rejected / quarantined / needs_more_review).
            for ev in self.uow.evidence.for_observation(o.id):
                if ev.status is not EvidenceStatus.APPROVED:
                    continue
                cited_evidence += 1
                digest = f"sha256:{ev.sha256[:16]}…" if ev.sha256 else "no hash"
                lines.append(
                    f"    - evidence `{str(ev.id)[:8]}` **{ev.title}** "
                    f"[{ev.evidence_type.value}] ({digest})"
                )
        lines.append("")

        lines.append(f"## Relationships ({len(relationships)})")
        if not relationships:
            lines.append("_No approved relationships yet._")
        for r in relationships:
            lines.append(
                f"- **{r.relationship_type.value}**: {entity_label(r.source_entity_id)} ↔ "
                f"{entity_label(r.target_entity_id)} "
                f"(confidence {r.confidence:.0%}; {len(r.observation_ids)} supporting observation(s))"
            )
        lines.append("")

        flagged = sum(1 for o in observations if o.handling.requires_legal_review)
        sensitive = sum(1 for o in observations if o.handling.sensitive)
        lines.append("## Handling")
        lines.append(f"- Approved evidence items cited: {cited_evidence}")
        lines.append(f"- Observations flagged for legal review: {flagged}")
        lines.append(f"- Observations marked sensitive: {sensitive}")
        lines.append("")

        return "\n".join(lines)
