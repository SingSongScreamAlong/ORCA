"""Report package service (v0.8 — partner-ready export).

Assembles an immutable export snapshot from a case's **approved** material only: a
Markdown report and a JSON evidence manifest, with content hashes. Proposed, rejected,
needs-more-review, and quarantined material is excluded by construction, and raw evidence
*files* are never bundled — only metadata and SHA-256 hashes. Generation and every
download are audited. See ``docs/v0.8_report_package_export.md``.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.audit import new_audit_entry
from app.core.content_store import sha256_hex
from app.core.security import Principal
from app.models.enums import EvidenceStatus, ReportStatus, ReviewStatus
from app.repositories.uow import UnitOfWork
from app.schemas.report_package import ReportPackageCounts, ReportPackageRead
from app.services.case_access import FORBIDDEN_MESSAGE, CaseAccessService
from app.services.errors import NotFoundError, PermissionDenied
from app.services.timeline_service import TimelineService

# A fixed timestamp for ZIP entries so the archive is byte-stable for identical content.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


class ReportPackageService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.access = CaseAccessService(uow)

    # --- queries -----------------------------------------------------------------

    def list_for_case(self, case_id: UUID) -> list[ReportPackageRead]:
        if self.uow.cases.get(case_id) is None:
            raise NotFoundError(f"Case {case_id} not found")
        return self.uow.report_packages.for_case(case_id)

    def list_for_principal(self, principal: Principal) -> list[ReportPackageRead]:
        """Packages across the cases the principal may access (admins see all)."""
        packages = self.uow.report_packages.list()
        scoped = self.access.accessible_case_ids(principal)
        if scoped is None:
            return packages
        return [p for p in packages if p.case_id in scoped]

    def get(self, package_id: UUID, principal: Principal) -> ReportPackageRead:
        package = self.uow.report_packages.get(package_id)
        if package is None:
            raise NotFoundError(f"Report package {package_id} not found")
        # Need-to-know: only members of the package's case (or an admin) may read it.
        if not self.access.can_view_reports(principal, package.case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)
        return package

    # --- generation --------------------------------------------------------------

    def generate(self, case_id: UUID, principal: Principal) -> ReportPackageRead:
        case = self.uow.cases.get(case_id)
        if case is None:
            raise NotFoundError(f"Case {case_id} not found")
        if not self.access.can_mutate(principal, case_id):
            raise PermissionDenied(FORBIDDEN_MESSAGE)

        approved_obs = [
            o for o in self.uow.observations.for_case(case_id) if o.status is ReviewStatus.APPROVED
        ]
        approved_obs_ids = {o.id for o in approved_obs}
        approved_rels = [
            r
            for r in self.uow.relationships.for_case(case_id)
            if r.status is ReviewStatus.APPROVED
            and all(oid in approved_obs_ids for oid in r.observation_ids)
        ]
        cited_evidence = [
            ev
            for o in approved_obs
            for ev in self.uow.evidence.for_observation(o.id)
            if ev.status is EvidenceStatus.APPROVED
        ]

        sensitive = any(
            o.handling.requires_legal_review or o.handling.sensitive for o in approved_obs
        ) or any(
            ev.legal_flags.requires_legal_review or ev.legal_flags.sensitive for ev in cited_evidence
        )
        handling_level = "sensitive" if sensitive else "standard"
        caveats = [
            "This package contains only approved material. Proposed, rejected, "
            "needs-more-review, and quarantined items are excluded.",
            "Raw evidence files are not included; each item is represented by metadata and "
            "its SHA-256 hash.",
            "All conclusions remain analyst-reviewed — ORCA proposes, analysts decide.",
        ]
        if sensitive:
            caveats.append(
                "Contains material flagged sensitive or for legal review — handle per the "
                "governing agreement."
            )

        now = datetime.now(UTC)
        package_id = uuid4()
        counts = ReportPackageCounts(
            approved_observations=len(approved_obs),
            approved_relationships=len(approved_rels),
            cited_evidence=len(cited_evidence),
        )
        manifest = {
            "package_id": str(package_id),
            "case_id": str(case.id),
            "case_title": case.title,
            "generated_at": now.isoformat(),
            "generated_by": principal.id,
            "handling_level": handling_level,
            "report_status": ReportStatus.FINAL.value,
            "caveats": caveats,
            "counts": {
                "approved_observations": counts.approved_observations,
                "approved_relationships": counts.approved_relationships,
                "cited_evidence": counts.cited_evidence,
            },
            "evidence": sorted(
                (self._manifest_entry(ev) for ev in cited_evidence),
                key=lambda e: e["evidence_id"],
            ),
        }
        manifest_text = self.manifest_text(manifest)
        manifest_sha = sha256_hex(manifest_text.encode("utf-8"))
        markdown = self._render_markdown(
            case, approved_obs, approved_rels, cited_evidence, handling_level, caveats,
            principal, now, counts,
        )
        report_sha = sha256_hex(markdown.encode("utf-8"))

        package = ReportPackageRead(
            id=package_id,
            case_id=case.id,
            title=f"Report package — {case.title}",
            status=ReportStatus.FINAL,
            handling_level=handling_level,
            generated_by=principal.id,
            counts=counts,
            caveats=caveats,
            report_sha256=report_sha,
            manifest_sha256=manifest_sha,
            report_markdown=markdown,
            manifest=manifest,
            created_at=now,
        )
        self.uow.report_packages.add(package)
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="report_package.generated",
                target_type="report_package",
                target_id=package.id,
                case_id=case.id,
                context={
                    "handling_level": handling_level,
                    "report_sha256": report_sha,
                    "manifest_sha256": manifest_sha,
                    "cited_evidence": counts.cited_evidence,
                },
            )
        )
        return package

    # --- downloads ---------------------------------------------------------------

    def report_markdown(self, package_id: UUID, principal: Principal) -> tuple[ReportPackageRead, str]:
        package = self.get(package_id, principal)
        self._audit_download(principal, package, "report_package.report_downloaded")
        return package, package.report_markdown

    def manifest_json(self, package_id: UUID, principal: Principal) -> tuple[ReportPackageRead, str]:
        package = self.get(package_id, principal)
        self._audit_download(principal, package, "report_package.manifest_downloaded")
        return package, self.manifest_text(package.manifest)

    def zip_bytes(self, package_id: UUID, principal: Principal) -> tuple[ReportPackageRead, bytes]:
        package = self.get(package_id, principal)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, text in (
                ("report.md", package.report_markdown),
                ("manifest.json", self.manifest_text(package.manifest)),
            ):
                info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, text)
        self._audit_download(principal, package, "report_package.downloaded")
        return package, buf.getvalue()

    # --- helpers -----------------------------------------------------------------

    @staticmethod
    def manifest_text(manifest: dict) -> str:
        """Canonical JSON serialization — stable so the recorded SHA-256 always matches."""
        return json.dumps(manifest, indent=2, sort_keys=True)

    def _audit_download(self, principal: Principal, package: ReportPackageRead, action: str) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action=action,
                target_type="report_package",
                target_id=package.id,
                case_id=package.case_id,
                context={"manifest_sha256": package.manifest_sha256},
            )
        )

    def _verification(self, ev) -> str:
        if ev.has_bytes and ev.sha256 and self.uow.content.exists(ev.sha256):
            data = self.uow.content.get(ev.sha256)
            return "verified" if data is not None and sha256_hex(data) == ev.sha256 else "mismatch"
        if ev.sha256:
            return "unverified_no_bytes"
        return "no_hash"

    def _manifest_entry(self, ev) -> dict:
        source = self.uow.sources.get(ev.source_id)
        return {
            "evidence_id": str(ev.id),
            "case_id": str(ev.case_id),
            "observation_id": str(ev.observation_id) if ev.observation_id else None,
            "title": ev.title,
            "evidence_type": ev.evidence_type.value,
            "original_filename": ev.original_filename,
            "mime_type": ev.mime_type,
            "size_bytes": ev.size_bytes,
            "sha256": ev.sha256,
            "status": ev.status.value,
            "source_id": str(ev.source_id),
            "source_name": source.name if source else None,
            "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
            "captured_by": ev.captured_by,
            "verification": self._verification(ev),
            "handling_notes": ev.handling_notes,
            "legal_flags": ev.legal_flags.model_dump(),
        }

    def _render_markdown(
        self, case, observations, relationships, evidence, handling_level, caveats,
        principal, now, counts,
    ) -> str:
        def entity_label(entity_id: UUID) -> str:
            entity = self.uow.entities.get(entity_id)
            return f"{entity.entity_type.value}:{entity.value}" if entity else str(entity_id)[:8]

        lines: list[str] = []
        lines.append(f"# Report package — {case.title}")
        lines.append("")
        lines.append(f"- **Generated:** {now.isoformat(timespec='seconds')}")
        lines.append(f"- **Generated by:** {principal.username} ({principal.role.value})")
        lines.append(f"- **Report status:** {ReportStatus.FINAL.value}")
        lines.append(f"- **Handling level:** {handling_level}")
        lines.append(
            f"- **Contents:** {counts.approved_observations} approved observation(s), "
            f"{counts.approved_relationships} approved relationship(s), "
            f"{counts.cited_evidence} cited evidence item(s)"
        )
        lines.append("")

        lines.append("## Export caveats")
        for c in caveats:
            lines.append(f"- {c}")
        lines.append("")

        lines.append("## Case")
        lines.append(f"- **Title:** {case.title}")
        lines.append(f"- **Status:** {case.status.value}")
        if case.summary:
            lines.append(f"- **Summary:** {case.summary}")
        if case.legal_notes:
            lines.append(f"- **Legal / handling:** {case.legal_notes}")
        lines.append("")

        lines.append(f"## Approved observations ({len(observations)})")
        if not observations:
            lines.append("_No approved observations._")
        for o in sorted(observations, key=lambda x: x.timestamp):
            source = self.uow.sources.get(o.source_id)
            source_name = source.name if source else str(o.source_id)[:8]
            lines.append(
                f"- `{str(o.id)[:8]}` {o.timestamp.date()} — {o.notes or '(no notes)'} "
                f"(source: {source_name}; confidence {o.confidence:.0%})"
            )
        lines.append("")

        lines.append(f"## Approved relationships ({len(relationships)})")
        if not relationships:
            lines.append("_No approved relationships._")
        for r in relationships:
            lines.append(
                f"- **{r.relationship_type.value}**: {entity_label(r.source_entity_id)} ↔ "
                f"{entity_label(r.target_entity_id)} (confidence {r.confidence:.0%}; "
                f"{len(r.observation_ids)} supporting observation(s))"
            )
        lines.append("")

        lines.append(f"## Cited evidence ({len(evidence)})")
        if not evidence:
            lines.append("_No approved evidence cited._")
        for ev in sorted(evidence, key=lambda e: str(e.id)):
            digest = f"sha256:{ev.sha256}" if ev.sha256 else "no hash"
            fname = ev.original_filename or "—"
            lines.append(
                f"- `{str(ev.id)[:8]}` **{ev.title}** [{ev.evidence_type.value}] — {fname} "
                f"({ev.mime_type or 'unknown'}, {ev.size_bytes or 0} bytes) "
                f"· {self._verification(ev)} · {digest}"
            )
        lines.append("")

        timeline = TimelineService(self.uow).for_case(case.id)
        lines.append(f"## Timeline summary ({len(timeline)})")
        if not timeline:
            lines.append("_No timeline events._")
        for e in timeline:
            lines.append(
                f"- {e.timestamp.isoformat(timespec='seconds')} — {e.kind.replace('_', ' ')}: "
                f"{e.summary}"
            )
        lines.append("")

        lines.append("## Exclusions")
        lines.append(
            "- Proposed, rejected, needs-more-review, and quarantined observations and "
            "evidence are excluded from this package."
        )
        lines.append(
            "- Raw evidence files, the case audit log, and the relationship graph are not "
            "part of partner exports."
        )
        lines.append("")
        return "\n".join(lines)
