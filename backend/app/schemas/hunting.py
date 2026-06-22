"""Hunting Grounds — source/NAI registry schemas (governance gate).

The registry is the executable form of ``docs/hunting_grounds_charter.md``: a source moves
``proposed → authorized → monitored`` (and ``suspended``/``retired``/``rejected``), and it can
**only** be authorized once a human records its lawful basis, access method, and jurisdiction.
Discovery (later) can only ever create ``proposed`` sources.
"""

from __future__ import annotations

from datetime import datetime
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
    aor: str = Field(min_length=1, description="Area of responsibility to add, e.g. 'Rhode Island'.")


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
    # Collection runs on the same cadence (each tick: discovery sweep, then collection sweep).
    collection_runs: int = 0
    last_collection_proposed: int | None = None
    last_collection_sources: int | None = None
    last_collection_error: str | None = None
