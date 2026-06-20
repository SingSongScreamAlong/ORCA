"""Typed definitions for the ORCA → Palantir Foundry ontology mapping (v0.9).

This package is a **specification and local scaffolding** layer only. It describes how
ORCA's domain model would map onto Foundry object types, link types, action types, and
permission rules, and exports that description as JSON for use against a real Foundry
tenant later. It performs **no** live Palantir calls, no sync, no external I/O beyond
writing local JSON via ``app.foundry_mapping.export``. See
``docs/v0.9_palantir_foundry_mapping.md``.

The mapping deliberately preserves every ORCA invariant (AI proposes / analysts decide;
relationships cite approved observations; reports cite approved evidence; need-to-know
case membership; partner export viewers get approved packages only; privileged actions
are audited; no CSAM handling).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class FoundryProperty:
    """A Foundry object-type property mapped from an ORCA field."""

    api_name: str  # Foundry property api name (camelCase)
    orca_field: str  # the ORCA source field (snake_case), or "" when derived/planned
    base_type: str  # string | integer | double | boolean | timestamp | array<string> | struct
    title: str
    required: bool = False
    sensitive: bool = False  # handling-sensitive / PII — never exposed to partner export
    mapping: str = "direct"  # direct | derived | planned
    description: str = ""


@dataclass(frozen=True)
class FoundryObjectType:
    api_name: str  # e.g. "OrcaCase"
    orca_model: str  # ORCA source model / schema
    title: str
    primary_key: str  # api_name of the primary-key property
    description: str
    properties: tuple[FoundryProperty, ...]
    status_property: str | None = None  # lifecycle/status property, if any


@dataclass(frozen=True)
class FoundryLinkType:
    api_name: str  # e.g. "caseContainsObservation"
    title: str
    source_object: str  # object-type api_name
    target_object: str  # object-type api_name
    cardinality: str  # ONE_TO_MANY | MANY_TO_ONE | MANY_TO_MANY
    orca_basis: str  # how the link is derived in ORCA
    description: str = ""


@dataclass(frozen=True)
class FoundryActionParameter:
    api_name: str
    base_type: str
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class FoundryActionType:
    api_name: str  # e.g. "createObservation"
    title: str
    orca_endpoint: str  # the ORCA API surface this corresponds to
    affected_object: str  # primary object-type api_name
    required_capability: str  # ORCA global capability gate
    required_case_role: str  # ORCA case-role gate ("" if not case-scoped)
    writes_audit: bool
    preserves_invariant: str  # the ORCA invariant this action upholds
    parameters: tuple[FoundryActionParameter, ...] = ()
    propose_only: bool = False  # True for assistive/AIP proposals that must route to review
    description: str = ""


@dataclass(frozen=True)
class CaseRolePermission:
    """How an ORCA case role maps to Foundry read/write/visibility for case material."""

    case_role: str
    can_read_material: bool
    can_mutate: bool
    can_review: bool
    can_manage_members: bool
    can_view_audit: bool
    can_access_raw_evidence: bool
    can_view_approved_reports: bool
    can_export_package: bool
    notes: str = ""


@dataclass(frozen=True)
class OntologySpec:
    version: str
    objects: tuple[FoundryObjectType, ...]
    links: tuple[FoundryLinkType, ...]
    actions: tuple[FoundryActionType, ...]
    permissions: tuple[CaseRolePermission, ...]
    forbidden_workflows: tuple[str, ...] = field(default_factory=tuple)
    invariants: tuple[str, ...] = field(default_factory=tuple)

    def object(self, api_name: str) -> FoundryObjectType | None:
        return next((o for o in self.objects if o.api_name == api_name), None)


def to_dict(value) -> dict | list:
    """Deterministic, JSON-serialisable form of any mapping dataclass (sorted on export)."""
    return asdict(value)
