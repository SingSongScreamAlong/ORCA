"""Hunting Grounds — source/NAI registry schemas (governance gate).

The registry is the executable form of ``docs/hunting_grounds_charter.md``: a source moves
``proposed → authorized → monitored`` (and ``suspended``/``retired``/``rejected``), and it can
**only** be authorized once a human records its lawful basis, access method, and jurisdiction.
Discovery (later) can only ever create ``proposed`` sources.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.enums import (
    EntityType,
    HuntingDiscoveryMethod,
    HuntingSourceCategory,
    HuntingSourceStatus,
)
from app.schemas.common import ConfidenceScore, ORCAModel


class HuntingEntityHint(ORCAModel):
    entity_type: EntityType
    value: str = Field(min_length=1)


class HuntingLeadCreate(ORCAModel):
    """A text-only lead from a monitored source. **No media fields** — leads carry text and
    entity hints only, so the pipeline cannot ingest imagery (CSAM-safe by construction)."""

    summary: str = Field(min_length=1, description="Text summary of the lead (no media).")
    observed_at: datetime | None = None
    confidence: ConfidenceScore = 0.4
    entities: list[HuntingEntityHint] = Field(default_factory=list)
    case_id: UUID | None = Field(default=None, description="Optional target case for the lead.")


class HuntingTransition(ORCAModel):
    """One immutable entry in a source's lifecycle history (append-only)."""

    from_status: HuntingSourceStatus | None
    to_status: HuntingSourceStatus
    by: str
    at: datetime
    note: str | None = None


class HuntingSourcePropose(ORCAModel):
    name: str = Field(min_length=1, description="Human label for the venue.")
    url: str = Field(min_length=1, description="Public host/URL of the venue.")
    category: HuntingSourceCategory = HuntingSourceCategory.OTHER
    aor: str = Field(min_length=1, description="Area of responsibility, e.g. 'Rhode Island'.")
    discovery_method: HuntingDiscoveryMethod = HuntingDiscoveryMethod.OPERATOR_SEED
    discovery_notes: str | None = None


class HuntingAuthorize(ORCAModel):
    """The authorization record. All three justification fields are required by the gate."""

    lawful_basis: str = Field(min_length=1, description="Why monitoring this source is lawful.")
    access_method: str = Field(min_length=1, description="How it will be accessed (e.g. licensed API).")
    jurisdiction: str = Field(min_length=1, description="Governing jurisdiction.")
    legal_review_note: str | None = Field(None, description="Legal reviewer's note / reference.")


class HuntingDecision(ORCAModel):
    """Reason for a reject / suspend / retire transition."""

    reason: str = Field(min_length=1)


class HuntingSourceRead(ORCAModel):
    id: UUID
    name: str
    url: str
    category: HuntingSourceCategory
    aor: str
    status: HuntingSourceStatus
    discovery_method: HuntingDiscoveryMethod
    discovery_notes: str | None
    proposed_by: str
    proposed_at: datetime
    # Authorization record (present once authorized):
    lawful_basis: str | None
    access_method: str | None
    jurisdiction: str | None
    legal_review_note: str | None
    authorized_by: str | None
    authorized_at: datetime | None
    last_decision_reason: str | None
    updated_at: datetime
    history: list[HuntingTransition]


class HuntingAorSummary(ORCAModel):
    """Rollup of the registry for one area of responsibility (or all)."""

    aor: str
    total: int
    monitored: int
    by_status: dict[str, int]  # status value -> count


class HuntingSummary(ORCAModel):
    aors: list[HuntingAorSummary]
    totals: HuntingAorSummary


class ReferralEntity(ORCAModel):
    """A located identifier in a referral package (pointer/metadata only — never media)."""

    entity_type: EntityType
    value: str
    # How many monitored venues this identifier was located from (>=2 ⇒ a cross-venue link).
    venue_count: int = 1


class IntelIdentifier(ORCAModel):
    """A located identifier and how widely it recurs across monitored venues (the case signal)."""

    entity_type: EntityType
    value: str
    source_count: int  # distinct monitored sources it appears in
    lead_count: int  # total leads referencing it
    sources: list[str]  # source names it appears in (for display)


class ProposedLink(ORCAModel):
    """A cross-venue relationship proposed into the review queue (analyst confirms)."""

    relationship_id: UUID
    source_value: str
    target_value: str
    relationship_type: str
    venue_count: int


class HuntingLinkResult(ORCAModel):
    aor: str | None
    proposed: int
    links: list[ProposedLink]


class HuntingIntelPicture(ORCAModel):
    """The AOR common operating picture: where the same actors/identifiers recur across venues.

    Cross-venue identifiers — one phone/wallet/handle/.onion located from two or more monitored
    venues — are the highest-value leads, the seam where separate listings become one case.
    Pointers and metadata only; no media.
    """

    aor: str | None
    monitored_sources: int
    leads: int
    identifiers: int
    cross_venue_count: int
    cross_venue: list[IntelIdentifier]  # identifiers in >=2 venues (sorted, strongest first)
    top_identifiers: list[IntelIdentifier]  # most-referenced overall


class IdentifierAppearance(ORCAModel):
    """One located sighting of an identifier — which monitored venue, where, and the text lead."""

    source_id: UUID
    source_name: str
    source_url: str
    aor: str
    observation_id: UUID
    summary: str
    observed_at: datetime
    status: str


class CoOccurringIdentifier(ORCAModel):
    """An identifier located alongside the subject in the same lead(s) — a link candidate."""

    entity_type: EntityType
    value: str
    shared_leads: int  # how many of the subject's leads this identifier also appears in


class IdentifierDossier(ORCAModel):
    """Everywhere one located identifier appears across monitored venues — the pivot answering
    'where is this phone/wallet/handle/.onion?' for an LE referral. Pointers/metadata only; no
    media. ``canonical`` notes the resolved type/value (the lookup is case/format-tolerant)."""

    entity_type: EntityType
    value: str
    venue_count: int  # distinct monitored venues it was located from
    lead_count: int  # total leads referencing it
    aors: list[str]  # distinct AORs it appears in
    appearances: list[IdentifierAppearance]
    co_occurring: list[CoOccurringIdentifier]  # identifiers sharing its leads (link candidates)


class OperationMember(ORCAModel):
    """One located identifier that belongs to an operation (a connected-component node)."""

    entity_type: EntityType
    value: str
    venue_count: int  # monitored venues this identifier appears in
    lead_count: int  # leads referencing it


class OperationCluster(ORCAModel):
    """The real linked **operation** around a seed identifier — its connected component.

    Two located identifiers are linked when they co-occur in the same text lead, or a relationship
    ties them; the operation is the transitive closure from the seed across those edges. Where the
    AOR rollup is "everything in a region," this is "everything in one network" — the seam that
    says *these scattered listings are one operation*, regardless of AOR. Pointers/metadata only.
    """

    seed_type: EntityType
    seed_value: str
    identifier_count: int
    venue_count: int  # distinct monitored venues the operation touches
    lead_count: int  # distinct leads across the operation
    aors: list[str]  # AORs the operation spans
    members: list[OperationMember]
    venues: list[ReferralSource]  # the venues it touches, with lawful basis
    relationships: list[ReferralRelationship]
    truncated: bool = False  # the component hit the traversal cap (very large network)


class OperationReferralPackage(ORCAModel):
    """An LE referral dossier for a whole **operation** — the connected component as a case file.

    The fourth and widest-by-network referral tier (after per-source, per-identifier, per-AOR):
    where the AOR rollup bounds the case by region, this bounds it by the actual linked network
    around a seed identifier. Carries the member identifiers, the venues (with lawful basis), the
    relationship map, and a ready-to-hand markdown summary. No media, by construction.
    """

    seed_type: EntityType
    seed_value: str
    generated_at: datetime
    generated_by: str
    identifier_count: int
    venue_count: int
    lead_count: int
    aors: list[str]
    members: list[OperationMember]
    venues: list[ReferralSource]
    relationships: list[ReferralRelationship]
    truncated: bool = False
    summary_markdown: str
    notice: str = (
        "Lawful OSINT referral. Contains pointers and metadata only — no media, no CSAM. "
        "Identifiers are leads for lawful follow-up; de-anonymization requires legal process."
    )


class IdentifierReferralPackage(ORCAModel):
    """A law-enforcement referral dossier centered on one located identifier.

    Where ``HuntingReferralPackage`` is per-venue, this is per-identifier: it aggregates every
    monitored venue a single phone/wallet/handle/.onion was located from (each with its lawful
    basis), the text leads citing it, the identifiers it co-occurs with, and the relationship map
    — the cross-venue case file for one actor/operation. No media, by construction.
    """

    entity_type: EntityType
    value: str
    generated_at: datetime
    generated_by: str
    venue_count: int
    lead_count: int
    aors: list[str]
    sources: list[ReferralSource]  # the venues it was located from, with lawful basis
    appearances: list[IdentifierAppearance]
    co_occurring: list[CoOccurringIdentifier]
    relationships: list[ReferralRelationship]
    summary_markdown: str
    notice: str = (
        "Lawful OSINT referral. Contains pointers and metadata only — no media, no CSAM. "
        "Identifiers are leads for lawful follow-up; de-anonymization requires legal process."
    )


class AorReferralPackage(ORCAModel):
    """A law-enforcement referral dossier for a whole area of responsibility — the operation rollup.

    Where ``HuntingReferralPackage`` is per-venue and ``IdentifierReferralPackage`` is per-identifier,
    this is per-AOR: it consolidates every monitored venue in the region (each with its lawful
    basis), all located identifiers (cross-venue ones flagged), the **cross-venue links** that tie
    separate venues into one operation, and the relationship map — the regional case file LE can act
    on. Pointers and metadata only; no media, by construction.
    """

    aor: str
    generated_at: datetime
    generated_by: str
    source_count: int
    identifier_count: int
    lead_count: int
    cross_venue_count: int
    sources: list[ReferralSource]  # the monitored venues in the AOR, with lawful basis
    located_identifiers: list[ReferralEntity]  # all located identifiers, cross-venue flagged
    cross_venue: list[IntelIdentifier]  # the >=2-venue identifiers (the strongest links)
    relationships: list[ReferralRelationship]
    summary_markdown: str
    notice: str = (
        "Lawful OSINT referral. Contains pointers and metadata only — no media, no CSAM. "
        "Identifiers are leads for lawful follow-up; de-anonymization requires legal process."
    )


class HuntingReferralRecord(ORCAModel):
    """One entry in the referral history — what was handed to LE, at what scope, by whom, and when.

    Derived from the append-only audit trail (``hunting.referral.*``); the accountability view over
    the four referral tiers. Pointers and counts only — it records that a dossier was generated, not
    its contents.
    """

    tier: Literal["source", "identifier", "aor", "operation"]
    target: str  # the subject (a venue name, an identifier, an AOR, or an operation seed)
    target_type: Literal[
        "hunting_source", "hunting_identifier", "hunting_aor", "hunting_operation"
    ]
    generated_by: str
    generated_at: datetime
    summary: str  # a short human-readable count summary (e.g. "12 identifiers · 3 venues")


class ReferralObservation(ORCAModel):
    id: UUID
    summary: str  # the text lead (observation notes)
    observed_at: datetime
    confidence: float
    status: str


class ReferralRelationship(ORCAModel):
    relationship_type: str
    source_value: str
    target_value: str
    confidence: float
    status: str


class ReferralSource(ORCAModel):
    """The monitored venue and the lawful basis it was watched under (provenance for LE)."""

    id: UUID
    name: str
    url: str
    category: HuntingSourceCategory
    aor: str
    status: HuntingSourceStatus
    lawful_basis: str | None
    access_method: str | None
    jurisdiction: str | None
    proposed_by: str
    authorized_by: str | None

    @classmethod
    def from_source(cls, source) -> ReferralSource:
        """Project a registry source (``HuntingSourceRead``) onto its LE-provenance subset."""
        return cls(
            id=source.id, name=source.name, url=source.url, category=source.category,
            aor=source.aor, status=source.status, lawful_basis=source.lawful_basis,
            access_method=source.access_method, jurisdiction=source.jurisdiction,
            proposed_by=source.proposed_by, authorized_by=source.authorized_by,
        )


class HuntingReferralPackage(ORCAModel):
    """A law-enforcement referral dossier for a Hunting Grounds source.

    Aggregates the **located identifiers**, the text leads, and the relationship map ORCA built
    from a monitored venue, with the source's provenance and lawful basis — **no media**, by
    construction. This is the "locate → case" output: pointers and patterns LE can act on.
    """

    source: ReferralSource
    generated_at: datetime
    generated_by: str
    observation_count: int
    identifier_count: int
    located_identifiers: list[ReferralEntity]
    observations: list[ReferralObservation]
    relationships: list[ReferralRelationship]
    summary_markdown: str
    notice: str = (
        "Lawful OSINT referral. Contains pointers and metadata only — no media, no CSAM. "
        "Identifiers are leads for lawful follow-up; de-anonymization requires legal process."
    )


class HuntingWatchlistEntry(ORCAModel):
    """One operator-managed area of responsibility the autonomous cadence sweeps for new venues."""

    aor: str
    added_by: str
    added_at: datetime


class HuntingWatchlistAdd(ORCAModel):
    aor: str = Field(
        min_length=1,
        max_length=255,  # matches the hunting_watchlist.aor / aor_key column
        description="Area of responsibility to add, e.g. 'Rhode Island'.",
    )


class HuntingDiscoveryCandidate(ORCAModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    category: HuntingSourceCategory = HuntingSourceCategory.OTHER
    notes: str | None = None


class HuntingDiscoveryRun(ORCAModel):
    """A batch of discovered candidate venues to propose into the registry."""

    aor: str = Field(min_length=1)
    candidates: list[HuntingDiscoveryCandidate] = Field(min_length=1)


class HuntingDiscoveryResult(ORCAModel):
    aor: str
    proposed: list[HuntingSourceRead]
    skipped_existing: int
    # Which provider produced these (set by the autonomous engine; None for a manual run).
    provider: str | None = None


class HuntingDiscoverySweepResult(ORCAModel):
    """The outcome of an autonomous sweep across a list of AORs (one ``result`` per AOR)."""

    aors: list[str]
    results: list[HuntingDiscoveryResult]
    total_proposed: int
    total_skipped: int
    provider: str | None = None


class HuntingDiscoveryStatus(ORCAModel):
    """Secret-free posture of the autonomous discovery engine (for the UI/operator).

    Reflects ``ORCA_HUNTING_DISCOVERY_*`` configuration — never the API key itself.
    """

    provider: str = Field(description="'disabled', 'mock', or 'http'.")
    enabled: bool
    configured: bool
    lawful_basis_recorded: bool = Field(
        description="Whether a lawful basis is recorded (required to enable the http provider)."
    )
    host: str | None = Field(default=None, description="Discovery source host (no path/secrets).")
    category: HuntingSourceCategory = Field(description="Default category applied to candidates.")
    aors: list[str] = Field(
        default_factory=list, description="Standing AOR watchlist a sweep covers by default."
    )
    tor_enabled: bool = Field(default=False, description="Reaching the source through a Tor proxy.")
    darkweb_acknowledged: bool = Field(
        default=False, description="Dark-web access acknowledged (counsel + LE deconfliction)."
    )


class HuntingCollectionStatus(ORCAModel):
    """Secret-free posture of the automated collection engine (text/metadata only; CSAM-safe).

    Reflects ``ORCA_HUNTING_COLLECTION_*`` configuration — never the API key itself.
    """

    provider: str = Field(description="'disabled', 'mock', or 'http'.")
    enabled: bool
    configured: bool
    lawful_basis_recorded: bool = Field(
        description="Whether a lawful basis is recorded (required to enable the http provider)."
    )
    host: str | None = Field(default=None, description="Collection source host (no path/secrets).")
    tor_enabled: bool = Field(default=False, description="Reaching the source through a Tor proxy.")
    darkweb_acknowledged: bool = Field(
        default=False, description="Dark-web access acknowledged (counsel + LE deconfliction)."
    )


class HuntingCollectionResult(ORCAModel):
    """The outcome of collecting from one monitored source — proposed observations only."""

    source_id: UUID
    source_name: str
    proposed_observation_ids: list[UUID]
    provider: str | None = None


class HuntingCollectionSweepResult(ORCAModel):
    """The outcome of an automated collection pass across all monitored sources."""

    results: list[HuntingCollectionResult]
    total_proposed: int
    sources_collected: int
    provider: str | None = None


class HuntingDiscoveryScheduleStatus(ORCAModel):
    """Posture of the continuous (scheduled) discovery loop — the autonomous cadence.

    ``enabled`` reflects ``ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED`` (config gate); ``paused`` is
    the runtime kill-switch an administrator can toggle; ``running`` is whether the loop task is
    live in this process. The ``last_*`` fields summarize the most recent automatic/triggered run.
    """

    enabled: bool
    interval_minutes: int
    limit_per_aor: int
    paused: bool
    running: bool
    runs: int
    last_run_at: datetime | None = None
    last_error: str | None = None
    last_total_proposed: int | None = None
    last_total_skipped: int | None = None
    last_aors: list[str] = Field(default_factory=list)
    # The targets the next sweep would cover — the live operator-managed watchlist (else the env
    # fallback), so the panel can preview the cadence's next run as the watchlist is edited.
    next_targets: list[str] = Field(default_factory=list)
    # Collection runs on the same cadence (each tick: discovery sweep, then collection sweep).
    collection_runs: int = 0
    last_collection_proposed: int | None = None
    last_collection_sources: int | None = None
    last_collection_error: str | None = None
