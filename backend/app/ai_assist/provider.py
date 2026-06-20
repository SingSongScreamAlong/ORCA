"""Provider abstraction for the Analyst Copilot (v1.0).

A provider turns approved case context into **proposed-only** suggestions. The default is
``MockProvider`` — fully deterministic, no network, no credentials — so the Copilot runs
locally and tests are reproducible. The ``AiProvider`` protocol is the seam a future
provider (e.g. Palantir AIP, with the same propose-only contract) would implement; no such
provider is included here, and none is required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID

from app.ai_assist.models import (
    AiCitationGap,
    AiProposedEntity,
    AiProposedRelationship,
    AiReportDraftSuggestion,
    AiSuggestion,
    AiUnsupportedClaimFlag,
)
from app.schemas.entity import EntityRead
from app.schemas.evidence import EvidenceItemRead
from app.schemas.observation import ObservationRead
from app.schemas.relationship import RelationshipRead
from app.schemas.timeline import TimelineEvent


@dataclass
class CopilotContext:
    """The approved-only material a Copilot call may reason over."""

    case_title: str
    observations: list[ObservationRead] = field(default_factory=list)
    relationships: list[RelationshipRead] = field(default_factory=list)
    evidence: list[EvidenceItemRead] = field(default_factory=list)
    entities: dict[UUID, EntityRead] = field(default_factory=dict)
    timeline: list[TimelineEvent] = field(default_factory=list)


@runtime_checkable
class AiProvider(Protocol):
    name: str

    def summarize(self, ctx: CopilotContext) -> tuple[str, list[AiSuggestion]]: ...

    def extract_entities(
        self, ctx: CopilotContext, texts: list[tuple[str, str]]
    ) -> list[AiProposedEntity]: ...

    def suggest_relationships(self, ctx: CopilotContext) -> list[AiProposedRelationship]: ...

    def draft_report_section(
        self, ctx: CopilotContext, section_title: str
    ) -> AiReportDraftSuggestion: ...

    def check_citations(
        self, ctx: CopilotContext, draft_text: str
    ) -> tuple[list[AiCitationGap], list[AiUnsupportedClaimFlag]]: ...

    def timeline_summary(self, ctx: CopilotContext) -> str: ...


_PHONE = re.compile(r"\+?\d[\d\s().\-]{6,}\d")
_HANDLE = re.compile(r"@(\w{2,})")
_ALIAS = re.compile(r"'([A-Z][a-zA-Z]{1,})'")
_CLAIM_VERBS = (
    "proves", "confirms", "establishes", "demonstrates", "is guilty", "is the same person",
    "identifies the", "shows that", "responsible for",
)


class MockProvider:
    """A deterministic, offline Copilot provider. No randomness, no I/O, no credentials."""

    name = "mock"

    def summarize(self, ctx: CopilotContext) -> tuple[str, list[AiSuggestion]]:
        entity_values = sorted({e.value for e in ctx.entities.values()})
        summary = (
            f"Case '{ctx.case_title}': {len(ctx.observations)} approved observation(s), "
            f"{len(ctx.relationships)} approved relationship(s), "
            f"{len(ctx.evidence)} approved evidence item(s)."
        )
        if entity_values:
            summary += " Entities referenced: " + ", ".join(entity_values[:10]) + "."
        return summary, self._review_gaps(ctx)

    def _review_gaps(self, ctx: CopilotContext) -> list[AiSuggestion]:
        gaps: list[AiSuggestion] = []
        for ev in ctx.evidence:
            if not ev.sha256:
                gaps.append(AiSuggestion(
                    kind="review_gap",
                    text=f"Evidence '{ev.title}' has no recorded hash to verify.",
                    rationale="Integrity cannot be confirmed without a SHA-256.",
                ))
        approved_obs_ids = {o.id for o in ctx.observations}
        for r in ctx.relationships:
            if not any(oid in approved_obs_ids for oid in r.observation_ids):
                gaps.append(AiSuggestion(
                    kind="review_gap",
                    text=f"Relationship {str(r.id)[:8]} lacks an approved supporting observation.",
                    rationale="Relationships must rest on approved observations.",
                ))
        gaps.append(AiSuggestion(
            kind="caveat",
            text="All findings are analyst-reviewed; this summary is an AI proposal only.",
        ))
        return gaps

    def extract_entities(
        self, ctx: CopilotContext, texts: list[tuple[str, str]]
    ) -> list[AiProposedEntity]:
        existing = {(e.entity_type.value, e.value): str(e.id) for e in ctx.entities.values()}
        found: dict[tuple[str, str], AiProposedEntity] = {}
        for obs_id, text in texts:
            for etype, value in self._candidates(text):
                key = (etype, value)
                if key in found:
                    if obs_id and obs_id not in found[key].source_observation_ids:
                        found[key].source_observation_ids.append(obs_id)
                    continue
                found[key] = AiProposedEntity(
                    entity_type=etype,
                    value=value,
                    confidence=0.5,
                    rationale="Pattern-extracted from approved case text; proposed candidate.",
                    source_observation_ids=[obs_id] if obs_id else [],
                    possible_duplicate_of=existing.get(key),
                )
        return [found[k] for k in sorted(found)]

    @staticmethod
    def _candidates(text: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for m in _PHONE.findall(text or ""):
            digits = re.sub(r"\D", "", m)
            if len(digits) >= 7:
                out.append(("phone_number", "+" + digits if not m.strip().startswith("+") else m.strip()))
        for h in _HANDLE.findall(text or ""):
            out.append(("username", h))
        for a in _ALIAS.findall(text or ""):
            out.append(("alias", a))
        return out

    def suggest_relationships(self, ctx: CopilotContext) -> list[AiProposedRelationship]:
        approved_pairs: set[frozenset[UUID]] = {
            frozenset((r.source_entity_id, r.target_entity_id)) for r in ctx.relationships
        }
        # Co-occurrence within a single approved observation suggests a candidate link.
        cooccur: dict[frozenset[UUID], list[str]] = {}
        for o in ctx.observations:
            ids = sorted(set(o.entity_ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair = frozenset((ids[i], ids[j]))
                    if pair in approved_pairs:
                        continue
                    cooccur.setdefault(pair, [])
                    if str(o.id) not in cooccur[pair]:
                        cooccur[pair].append(str(o.id))
        out: list[AiProposedRelationship] = []
        for pair, obs_ids in cooccur.items():
            a, b = sorted(pair, key=str)
            ea, eb = ctx.entities.get(a), ctx.entities.get(b)
            if ea is None or eb is None:
                continue
            out.append(AiProposedRelationship(
                relationship_type="appears_with",
                source_value=ea.value,
                target_value=eb.value,
                confidence=0.4,
                rationale=f"Co-occur in {len(obs_ids)} approved observation(s); candidate only.",
                supporting_observation_ids=sorted(obs_ids),
            ))
        return sorted(out, key=lambda r: (r.source_value, r.target_value))

    def draft_report_section(
        self, ctx: CopilotContext, section_title: str
    ) -> AiReportDraftSuggestion:
        lines = [
            f"## {section_title}",
            "",
            f"_AI-proposed draft from {len(ctx.observations)} approved observation(s). "
            "Requires analyst review before use._",
            "",
        ]
        cited: list[str] = []
        for o in sorted(ctx.observations, key=lambda x: x.timestamp):
            lines.append(f"- {o.timestamp.date()}: {o.notes or '(no notes)'} (obs {str(o.id)[:8]})")
            cited.append(str(o.id))
        if not ctx.observations:
            lines.append("_No approved observations to draft from._")
        return AiReportDraftSuggestion(
            section_title=section_title, draft_markdown="\n".join(lines), cited_observation_ids=cited
        )

    def check_citations(
        self, ctx: CopilotContext, draft_text: str
    ) -> tuple[list[AiCitationGap], list[AiUnsupportedClaimFlag]]:
        gaps: list[AiCitationGap] = []
        unsupported: list[AiUnsupportedClaimFlag] = []
        approved_ids = {str(o.id)[:8] for o in ctx.observations}
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", draft_text or "") if s.strip()]
        for idx, sentence in enumerate(sentences):
            lower = sentence.lower()
            has_citation = "obs " in lower or any(sid in sentence for sid in approved_ids)
            if any(verb in lower for verb in _CLAIM_VERBS) and not has_citation:
                unsupported.append(AiUnsupportedClaimFlag(
                    claim=sentence,
                    reason="Assertive claim with no cited approved observation.",
                ))
            elif "evidence" in lower and not has_citation:
                gaps.append(AiCitationGap(
                    location=f"sentence {idx + 1}",
                    claim=sentence,
                    issue="missing_citation",
                ))
        return gaps, unsupported

    def timeline_summary(self, ctx: CopilotContext) -> str:
        if not ctx.timeline:
            return "No approved timeline events yet."
        times = sorted(e.timestamp for e in ctx.timeline)
        kinds: dict[str, int] = {}
        for e in ctx.timeline:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        breakdown = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(kinds.items()))
        return (
            f"{len(ctx.timeline)} approved timeline event(s) from "
            f"{times[0].date()} to {times[-1].date()}. {breakdown}."
        )


def build_provider() -> AiProvider:
    """Return the configured provider. Defaults to the offline, credential-free mock."""
    from app.core.config import get_settings

    settings = get_settings()
    # Only the mock provider ships with ORCA; a real provider would be added here behind
    # its own configuration and would implement the same propose-only contract. With no
    # external provider configured, the Copilot stays fully local.
    if settings.ai_provider != "mock":
        return MockProvider()
    return MockProvider()
