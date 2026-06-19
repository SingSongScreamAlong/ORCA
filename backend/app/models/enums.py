"""Enumerations shared by ORM models and API schemas.

These mirror ``ontology/schema/enums.yaml``. Keep the two in sync.
"""

from __future__ import annotations

from enum import Enum


class ConfidenceBand(str, Enum):
    UNVERIFIED = "unverified"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"


def band_for(confidence: float) -> ConfidenceBand:
    """Map a numeric confidence in [0, 1] to its qualitative band."""
    if confidence < 0.20:
        return ConfidenceBand.UNVERIFIED
    if confidence < 0.40:
        return ConfidenceBand.LOW
    if confidence < 0.70:
        return ConfidenceBand.MEDIUM
    if confidence < 0.90:
        return ConfidenceBand.HIGH
    return ConfidenceBand.CONFIRMED


class Origin(str, Enum):
    SYSTEM_PROPOSED = "system_proposed"
    ANALYST_CREATED = "analyst_created"
    IMPORTED = "imported"


class ReviewStatus(str, Enum):
    """Approval lifecycle shared by observations, relationships, and review items.

    These are the four states the analyst interface shows as status badges.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_REVIEW = "needs_more_review"


class EntityType(str, Enum):
    PHONE_NUMBER = "phone_number"
    ALIAS = "alias"
    ACCOUNT = "account"
    USERNAME = "username"
    LOCATION = "location"
    VEHICLE = "vehicle"
    IMAGE = "image"
    ADVERTISEMENT = "advertisement"
    TATTOO_MARKER = "tattoo_marker"


class RelationshipType(str, Enum):
    SHARED_PHONE = "shared_phone"
    SHARED_IMAGE = "shared_image"
    SHARED_LOCATION = "shared_location"
    SHARED_ACCOUNT = "shared_account"
    APPEARS_WITH = "appears_with"
    ANALYST_CONFIRMED = "analyst_confirmed"


# Relationship types the system may propose from evidence. ``analyst_confirmed`` is
# deliberately excluded — it can only be set by a person.
SYSTEM_PROPOSABLE_RELATIONSHIP_TYPES: frozenset[RelationshipType] = frozenset(
    {
        RelationshipType.SHARED_PHONE,
        RelationshipType.SHARED_IMAGE,
        RelationshipType.SHARED_LOCATION,
        RelationshipType.SHARED_ACCOUNT,
        RelationshipType.APPEARS_WITH,
    }
)


class EvidenceType(str, Enum):
    SCREENSHOT = "screenshot"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    WEB_ARCHIVE = "web_archive"
    ANALYST_NOTE = "analyst_note"
    PARTNER_FILE = "partner_file"
    OTHER = "other"


class EvidenceStatus(str, Enum):
    """Evidence-item lifecycle. Extends the review states with ``quarantined`` for
    material that must be isolated pending handling decisions."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_REVIEW = "needs_more_review"
    QUARANTINED = "quarantined"


class SourceType(str, Enum):
    WEBSITE = "website"
    DATASET = "dataset"
    MANUAL_UPLOAD = "manual_upload"
    TIP = "tip"
    DOCUMENT = "document"


class SourceReliability(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClusterStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class CaseStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    FINAL = "final"


class ReviewItemType(str, Enum):
    PROPOSED_OBSERVATION = "proposed_observation"
    PROPOSED_RELATIONSHIP = "proposed_relationship"
    PROPOSED_CLUSTER = "proposed_cluster"
    FLAGGED_OBSERVATION = "flagged_observation"
