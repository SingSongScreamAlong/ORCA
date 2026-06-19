"""Hunting Grounds interfaces — definitions only.

These Protocols and dataclasses describe what a collector must provide. They are
intentionally free of implementation: collection is out of scope for this skeleton.
The shapes are chosen so that a collector can only *produce* evidence and proposed
observations, never confirm anything.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.models.enums import EntityType, EvidenceType, SourceType


@dataclass(frozen=True)
class CollectionTarget:
    """A description of where a collector should look.

    Targets are configuration, not behavior. They never include credentials for, or
    instructions to gain unauthorized access to, any system.
    """

    source_type: SourceType
    locator: str  # e.g. a public URL or dataset identifier
    label: str
    notes: str | None = None


@dataclass(frozen=True)
class PreservedEvidence:
    """The result of preserving an artifact: bytes are stored, integrity is anchored."""

    evidence_type: EvidenceType
    sha256: str
    storage_uri: str
    content_type: str | None
    captured_at: datetime


@dataclass(frozen=True)
class ExtractedEntity:
    """A candidate entity extracted from collected material. A proposal, not a fact."""

    entity_type: EntityType
    value: str
    confidence: float


@dataclass(frozen=True)
class CollectedItem:
    """One unit of collected material, ready to become an observation + evidence.

    A collector emits these; the platform turns them into an append-only observation
    (attributed to the source) plus preserved evidence. Extracted entities are
    proposals routed through review.
    """

    target: CollectionTarget
    observed_at: datetime
    summary: str
    evidence: list[PreservedEvidence] = field(default_factory=list)
    extracted_entities: list[ExtractedEntity] = field(default_factory=list)


@runtime_checkable
class EvidencePreserver(Protocol):
    """Captures an artifact and returns preserved, hashed evidence."""

    def preserve(
        self, raw: bytes, evidence_type: EvidenceType, content_type: str | None
    ) -> PreservedEvidence:
        ...


@runtime_checkable
class EntityExtractor(Protocol):
    """Proposes candidate entities from collected material."""

    def extract(self, item: CollectedItem) -> Iterable[ExtractedEntity]:
        ...


@runtime_checkable
class Collector(Protocol):
    """Monitors a target and yields collected items.

    Implementations are out of scope for this skeleton. The signature constrains a
    collector to *yielding observations-to-be*; it has no method that confirms,
    decides, or writes to the confirmed graph.
    """

    def collect(self, target: CollectionTarget) -> Iterator[CollectedItem]:
        ...
