"""Report package API schemas (v0.8 — partner-ready export).

A report package is an immutable, partner-ready export snapshot built from a case's
**approved** material only: a Markdown report plus a JSON evidence manifest, with content
hashes. Proposed, rejected, needs-more-review, and quarantined material is excluded by
construction. Raw evidence *files* are never bundled — evidence is represented by metadata
and SHA-256 hashes. See ``docs/v0.8_report_package_export.md``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import ReportStatus
from app.schemas.common import ORCAModel


class ReportPackageCounts(ORCAModel):
    approved_observations: int
    approved_relationships: int
    cited_evidence: int


class ReportPackageSummary(ORCAModel):
    """Package metadata (no bodies) — for listing and the metadata view."""

    id: UUID
    case_id: UUID
    title: str
    status: ReportStatus
    handling_level: str
    generated_by: str
    counts: ReportPackageCounts
    caveats: list[str]
    report_sha256: str
    manifest_sha256: str
    created_at: datetime


class ReportPackageRead(ReportPackageSummary):
    """The full stored package, including the report markdown and evidence manifest."""

    report_markdown: str
    manifest: dict
