"""Request/response models for the Analyst Copilot (v1.0).

Every AI output is **proposed only**. Results carry explicit metadata —
``generated_by_ai``, ``provider``, ``generated_at``, ``source_material_ids``,
``status = "proposed"``, ``requires_human_review = True`` — so nothing can be mistaken for
authoritative case material. AI never writes case material directly; an analyst must act
on a suggestion through the normal, audited workflow. See
``docs/v1.0_aip_assisted_analyst_copilot.md``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORCAModel


class AiMeta(ORCAModel):
    """Provenance stamped on every AI result so it is never mistaken for fact."""

    generated_by_ai: bool = True
    provider: str
    generated_at: datetime
    source_material_ids: list[str] = Field(default_factory=list)
    status: str = "proposed"
    requires_human_review: bool = True


class AiSuggestion(ORCAModel):
    kind: str  # e.g. "review_gap", "caveat", "duplicate_entity"
    text: str
    rationale: str | None = None


class AiProposedEntity(ORCAModel):
    entity_type: str
    value: str
    confidence: float
    rationale: str
    source_observation_ids: list[str] = Field(default_factory=list)
    possible_duplicate_of: str | None = None  # existing entity id, if a likely match


class AiProposedRelationship(ORCAModel):
    relationship_type: str
    source_value: str
    target_value: str
    confidence: float
    rationale: str
    supporting_observation_ids: list[str] = Field(default_factory=list)


class AiReportDraftSuggestion(ORCAModel):
    section_title: str
    draft_markdown: str
    cited_observation_ids: list[str] = Field(default_factory=list)


class AiCitationGap(ORCAModel):
    location: str
    claim: str
    issue: str  # "missing_citation"


class AiUnsupportedClaimFlag(ORCAModel):
    claim: str
    reason: str


class AiAssistRequest(ORCAModel):
    """Optional inputs; which fields are used depends on the endpoint."""

    note: str | None = Field(default=None, description="Analyst note to extract from.")
    section_title: str | None = Field(default=None, description="Report section to draft.")
    draft_text: str | None = Field(default=None, description="Draft text to check for citations.")
    instructions: str | None = None


class AiAssistResult(ORCAModel):
    """A single, unified, proposed-only result envelope for every Copilot endpoint."""

    case_id: UUID
    assist_type: str
    meta: AiMeta
    summary: str | None = None
    suggestions: list[AiSuggestion] = Field(default_factory=list)
    proposed_entities: list[AiProposedEntity] = Field(default_factory=list)
    proposed_relationships: list[AiProposedRelationship] = Field(default_factory=list)
    report_draft: AiReportDraftSuggestion | None = None
    citation_gaps: list[AiCitationGap] = Field(default_factory=list)
    unsupported_claims: list[AiUnsupportedClaimFlag] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
