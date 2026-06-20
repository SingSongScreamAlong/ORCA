"""ORCA → Foundry object-type mappings (v0.9).

Each ORCA domain model maps to a Foundry object type. Properties carry their ORCA source
field and a mapping kind: ``direct`` (a stored ORCA field), ``derived`` (computed by
ORCA, e.g. an evidence verification status), or ``planned`` (a target Foundry property
not yet present in the ORCA model). Sensitive properties are flagged so the permission
layer can keep them out of partner exports.
"""

from __future__ import annotations

from app.foundry_mapping.types import FoundryObjectType, FoundryProperty


def _p(api_name, orca_field, base_type, title, **kw) -> FoundryProperty:
    return FoundryProperty(
        api_name=api_name, orca_field=orca_field, base_type=base_type, title=title, **kw
    )


OrcaCase = FoundryObjectType(
    api_name="OrcaCase",
    orca_model="app.schemas.case.CaseRead",
    title="ORCA Case",
    primary_key="caseId",
    status_property="status",
    description="A curated view over evidence; the unit of need-to-know access control.",
    properties=(
        _p("caseId", "id", "string", "Case ID", required=True),
        _p("title", "title", "string", "Title", required=True),
        _p("summary", "summary", "string", "Summary"),
        _p("status", "status", "string", "Status", required=True),
        _p("priority", "", "string", "Priority", mapping="planned"),
        _p("createdAt", "created_at", "timestamp", "Created at", required=True),
        _p("createdBy", "owner", "string", "Created by"),
        _p("assignedTo", "", "string", "Assigned to", mapping="planned"),
        _p("partnerAgency", "", "string", "Partner agency", mapping="planned"),
        _p("handlingLevel", "", "string", "Handling level", mapping="derived",
           description="Derived from cited material (standard/sensitive)."),
        _p("legalBasis", "legal_notes", "string", "Legal basis"),
        _p("lastActivityAt", "updated_at", "timestamp", "Last activity at"),
    ),
)

OrcaUser = FoundryObjectType(
    api_name="OrcaUser",
    orca_model="app.schemas.user.UserRead",
    title="ORCA User",
    primary_key="userId",
    description="An authenticated actor with a global role (RBAC).",
    properties=(
        _p("userId", "id", "string", "User ID", required=True),
        _p("username", "username", "string", "Username", required=True),
        _p("displayName", "display_name", "string", "Display name"),
        _p("globalRole", "role", "string", "Global role", required=True),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaCaseMembership = FoundryObjectType(
    api_name="OrcaCaseMembership",
    orca_model="app.schemas.user.CaseMemberRead",
    title="ORCA Case Membership",
    primary_key="membershipId",
    status_property="status",
    description="A user's active/inactive/revoked membership and case role in a case.",
    properties=(
        _p("membershipId", "id", "string", "Membership ID", required=True),
        _p("caseId", "case_id", "string", "Case ID", required=True),
        _p("userId", "user_id", "string", "User ID", required=True),
        _p("caseRole", "case_role", "string", "Case role", required=True),
        _p("status", "status", "string", "Status", required=True),
        _p("assignedBy", "assigned_by", "string", "Assigned by"),
        _p("assignedAt", "assigned_at", "timestamp", "Assigned at"),
    ),
)

OrcaSource = FoundryObjectType(
    api_name="OrcaSource",
    orca_model="app.schemas.source.SourceRead",
    title="ORCA Source",
    primary_key="sourceId",
    description="The provenance of an observation or evidence item.",
    properties=(
        _p("sourceId", "id", "string", "Source ID", required=True),
        _p("caseId", "", "string", "Case ID", mapping="planned",
           description="Sources are referenced by case-scoped objects in ORCA."),
        _p("sourceType", "source_type", "string", "Source type", required=True),
        _p("sourceUri", "identifier", "string", "Source URI"),
        _p("sourceTitle", "name", "string", "Source title", required=True),
        _p("captureTime", "", "timestamp", "Capture time", mapping="planned"),
        _p("capturedBy", "", "string", "Captured by", mapping="planned"),
        _p("archiveReference", "", "string", "Archive reference", mapping="planned"),
        _p("sourceHash", "", "string", "Source hash", mapping="planned"),
        _p("accessMethod", "", "string", "Access method", mapping="planned"),
        _p("handlingNotes", "description", "string", "Handling notes", sensitive=True),
        _p("legalFlags", "", "struct", "Legal flags", mapping="planned"),
        _p("reliabilityScore", "reliability", "string", "Reliability"),
    ),
)

OrcaObservation = FoundryObjectType(
    api_name="OrcaObservation",
    orca_model="app.schemas.observation.ObservationRead",
    title="ORCA Observation",
    primary_key="observationId",
    status_property="status",
    description="A recorded fact awaiting or having human review. Atomic unit of truth.",
    properties=(
        _p("observationId", "id", "string", "Observation ID", required=True),
        _p("caseId", "case_id", "string", "Case ID"),
        _p("sourceId", "source_id", "string", "Source ID", required=True),
        _p("text", "notes", "string", "Text", sensitive=True),
        _p("observationType", "", "string", "Observation type", mapping="planned"),
        _p("status", "status", "string", "Status", required=True),
        _p("confidence", "confidence", "double", "Confidence"),
        _p("origin", "", "string", "Origin", mapping="planned",
           description="System-proposed vs analyst-created; proposals route to review."),
        _p("createdAt", "created_at", "timestamp", "Created at"),
        _p("createdBy", "collector", "string", "Created by"),
        _p("reviewedAt", "decided_at", "timestamp", "Reviewed at"),
        _p("reviewedBy", "decided_by", "string", "Reviewed by"),
        _p("reviewNotes", "", "string", "Review notes", mapping="planned", sensitive=True),
    ),
)

OrcaEvidenceItem = FoundryObjectType(
    api_name="OrcaEvidenceItem",
    orca_model="app.schemas.evidence.EvidenceItemRead",
    title="ORCA Evidence Item",
    primary_key="evidenceId",
    status_property="status",
    description="Case-scoped, hash-verifiable evidence. Raw bytes are never exported.",
    properties=(
        _p("evidenceId", "id", "string", "Evidence ID", required=True),
        _p("caseId", "case_id", "string", "Case ID", required=True),
        _p("sourceId", "source_id", "string", "Source ID", required=True),
        _p("observationId", "observation_id", "string", "Observation ID"),
        _p("title", "title", "string", "Title", required=True),
        _p("description", "description", "string", "Description", sensitive=True),
        _p("evidenceType", "evidence_type", "string", "Evidence type", required=True),
        _p("storageUri", "storage_uri", "string", "Storage URI", sensitive=True,
           description="Content-addressed pointer; bytes are never bundled into exports."),
        _p("originalFilename", "original_filename", "string", "Original filename"),
        _p("mimeType", "mime_type", "string", "MIME type"),
        _p("sizeBytes", "size_bytes", "integer", "Size (bytes)"),
        _p("sha256", "sha256", "string", "SHA-256", description="Integrity anchor."),
        _p("capturedAt", "captured_at", "timestamp", "Captured at"),
        _p("capturedBy", "captured_by", "string", "Captured by"),
        _p("accessMethod", "access_method", "string", "Access method"),
        _p("legalFlags", "legal_flags", "struct", "Legal flags", sensitive=True),
        _p("handlingNotes", "handling_notes", "string", "Handling notes", sensitive=True),
        _p("status", "status", "string", "Status", required=True),
        _p("verificationStatus", "", "string", "Verification status", mapping="derived",
           description="Computed by re-hashing stored bytes (verified/mismatch/none)."),
        _p("createdBy", "created_by", "string", "Created by"),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaEntity = FoundryObjectType(
    api_name="OrcaEntity",
    orca_model="app.schemas.entity.EntityRead",
    title="ORCA Entity",
    primary_key="entityId",
    description="A canonical, deduplicated entity that persists beyond any single case.",
    properties=(
        _p("entityId", "id", "string", "Entity ID", required=True),
        _p("entityType", "entity_type", "string", "Entity type", required=True),
        _p("value", "value", "string", "Value", required=True, sensitive=True),
        _p("confidence", "confidence", "double", "Confidence"),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaRelationship = FoundryObjectType(
    api_name="OrcaRelationship",
    orca_model="app.schemas.relationship.RelationshipRead",
    title="ORCA Relationship",
    primary_key="relationshipId",
    status_property="status",
    description="A link between two entities; only approved relationships are traversable.",
    properties=(
        _p("relationshipId", "id", "string", "Relationship ID", required=True),
        _p("caseId", "case_id", "string", "Case ID"),
        _p("sourceEntityId", "source_entity_id", "string", "Source entity ID", required=True),
        _p("targetEntityId", "target_entity_id", "string", "Target entity ID", required=True),
        _p("relationshipType", "relationship_type", "string", "Relationship type", required=True),
        _p("confidence", "confidence", "double", "Confidence"),
        _p("origin", "origin", "string", "Origin"),
        _p("status", "status", "string", "Status", required=True),
        _p("observationIds", "observation_ids", "array<string>", "Supporting observation IDs",
           description="Must reference approved observations."),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaReviewDecision = FoundryObjectType(
    api_name="OrcaReviewDecision",
    orca_model="app.schemas.review.ReviewItemRead (decided)",
    title="ORCA Review Decision",
    primary_key="reviewItemId",
    status_property="status",
    description="The recorded human decision on a proposed observation/evidence/relationship.",
    properties=(
        _p("reviewItemId", "id", "string", "Review item ID", required=True),
        _p("caseId", "case_id", "string", "Case ID"),
        _p("subjectType", "subject_type", "string", "Subject type", required=True),
        _p("subjectId", "subject_id", "string", "Subject ID", required=True),
        _p("status", "status", "string", "Decision status", required=True),
        _p("proposedBy", "created_by", "string", "Proposed by"),
        _p("decidedBy", "decided_by", "string", "Decided by"),
        _p("decidedAt", "decided_at", "timestamp", "Decided at"),
        _p("rationale", "rationale", "string", "Rationale", sensitive=True),
    ),
)

OrcaTask = FoundryObjectType(
    api_name="OrcaTask",
    orca_model="app.schemas.review.ReviewItemRead (open)",
    title="ORCA Task",
    primary_key="taskId",
    status_property="status",
    description="An open review-queue work item awaiting an analyst decision.",
    properties=(
        _p("taskId", "id", "string", "Task ID", required=True),
        _p("caseId", "case_id", "string", "Case ID"),
        _p("itemType", "item_type", "string", "Item type", required=True),
        _p("subjectType", "subject_type", "string", "Subject type", required=True),
        _p("subjectId", "subject_id", "string", "Subject ID", required=True),
        _p("status", "status", "string", "Status", required=True),
        _p("createdBy", "created_by", "string", "Created by"),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaReport = FoundryObjectType(
    api_name="OrcaReport",
    orca_model="app.schemas.report.ReportRead",
    title="ORCA Report",
    primary_key="reportId",
    status_property="status",
    description="A draft/final report drawing only on approved evidence.",
    properties=(
        _p("reportId", "id", "string", "Report ID", required=True),
        _p("caseId", "case_id", "string", "Case ID", required=True),
        _p("title", "title", "string", "Title", required=True),
        _p("author", "author", "string", "Author"),
        _p("status", "status", "string", "Status", required=True),
        _p("body", "body", "string", "Body", sensitive=True),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaReportPackage = FoundryObjectType(
    api_name="OrcaReportPackage",
    orca_model="app.schemas.report_package.ReportPackageRead",
    title="ORCA Report Package",
    primary_key="packageId",
    status_property="status",
    description="An immutable partner-ready export: report + evidence manifest (hashes only).",
    properties=(
        _p("packageId", "id", "string", "Package ID", required=True),
        _p("caseId", "case_id", "string", "Case ID", required=True),
        _p("title", "title", "string", "Title", required=True),
        _p("status", "status", "string", "Status", required=True),
        _p("handlingLevel", "handling_level", "string", "Handling level"),
        _p("generatedBy", "generated_by", "string", "Generated by"),
        _p("reportSha256", "report_sha256", "string", "Report SHA-256"),
        _p("manifestSha256", "manifest_sha256", "string", "Manifest SHA-256"),
        _p("citedEvidenceCount", "", "integer", "Cited evidence count", mapping="derived"),
        _p("createdAt", "created_at", "timestamp", "Created at"),
    ),
)

OrcaAuditEvent = FoundryObjectType(
    api_name="OrcaAuditEvent",
    orca_model="app.core.audit.AuditEntry",
    title="ORCA Audit Event",
    primary_key="auditId",
    description="An append-only record of a consequential action. Never updated or deleted.",
    properties=(
        _p("auditId", "id", "string", "Audit ID", required=True),
        _p("actorId", "actor_id", "string", "Actor ID", required=True),
        _p("action", "action", "string", "Action", required=True),
        _p("targetType", "target_type", "string", "Target type", required=True),
        _p("targetId", "target_id", "string", "Target ID", required=True),
        _p("caseId", "case_id", "string", "Case ID"),
        _p("context", "context", "struct", "Context"),
        _p("createdAt", "created_at", "timestamp", "Created at", required=True),
    ),
)

OBJECT_TYPES: tuple[FoundryObjectType, ...] = (
    OrcaCase,
    OrcaUser,
    OrcaCaseMembership,
    OrcaSource,
    OrcaObservation,
    OrcaEvidenceItem,
    OrcaEntity,
    OrcaRelationship,
    OrcaReviewDecision,
    OrcaTask,
    OrcaReport,
    OrcaReportPackage,
    OrcaAuditEvent,
)
