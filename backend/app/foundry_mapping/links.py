"""ORCA → Foundry link-type mappings (v0.9).

Each link mirrors a relationship ORCA already enforces in its relational record. No link
implies a capability ORCA does not already have; in particular, traversable relationships
between entities reflect only **approved** ORCA relationships.
"""

from __future__ import annotations

from app.foundry_mapping.types import FoundryLinkType


def _l(api_name, title, source, target, cardinality, basis, description="") -> FoundryLinkType:
    return FoundryLinkType(
        api_name=api_name, title=title, source_object=source, target_object=target,
        cardinality=cardinality, orca_basis=basis, description=description,
    )


LINK_TYPES: tuple[FoundryLinkType, ...] = (
    _l("caseContainsSource", "Case contains Source", "OrcaCase", "OrcaSource",
       "ONE_TO_MANY", "Sources referenced by a case's observations/evidence."),
    _l("caseContainsObservation", "Case contains Observation", "OrcaCase", "OrcaObservation",
       "ONE_TO_MANY", "Observation.case_id."),
    _l("caseContainsEvidenceItem", "Case contains Evidence Item", "OrcaCase", "OrcaEvidenceItem",
       "ONE_TO_MANY", "EvidenceItem.case_id."),
    _l("caseContainsEntity", "Case contains Entity", "OrcaCase", "OrcaEntity",
       "MANY_TO_MANY", "Entities referenced by a case's observations (entities persist across cases)."),
    _l("caseContainsRelationship", "Case contains Relationship", "OrcaCase", "OrcaRelationship",
       "ONE_TO_MANY", "Relationship.case_id."),
    _l("caseContainsReport", "Case contains Report", "OrcaCase", "OrcaReport",
       "ONE_TO_MANY", "Report.case_id."),
    _l("caseContainsReportPackage", "Case contains Report Package", "OrcaCase", "OrcaReportPackage",
       "ONE_TO_MANY", "ReportPackage.case_id."),
    _l("caseHasCaseMembership", "Case has Case Membership", "OrcaCase", "OrcaCaseMembership",
       "ONE_TO_MANY", "CaseMembership.case_id — the need-to-know roster."),
    _l("sourceSupportsObservation", "Source supports Observation", "OrcaSource", "OrcaObservation",
       "ONE_TO_MANY", "Observation.source_id."),
    _l("observationCitesEvidenceItem", "Observation cites Evidence Item",
       "OrcaObservation", "OrcaEvidenceItem", "ONE_TO_MANY", "EvidenceItem.observation_id."),
    _l("observationSupportsRelationship", "Observation supports Relationship",
       "OrcaObservation", "OrcaRelationship", "MANY_TO_MANY",
       "Relationship.observation_ids — supporting observations must be approved."),
    _l("entityParticipatesInRelationship", "Entity participates in Relationship",
       "OrcaEntity", "OrcaRelationship", "MANY_TO_MANY",
       "Relationship.source_entity_id / target_entity_id."),
    _l("reportCitesObservation", "Report cites Observation", "OrcaReport", "OrcaObservation",
       "MANY_TO_MANY", "Reports cite approved observations only."),
    _l("reportPackageIncludesReport", "Report Package includes Report",
       "OrcaReportPackage", "OrcaReport", "ONE_TO_ONE",
       "The package's rendered report (approved material only)."),
    _l("reportPackageIncludesEvidenceManifest", "Report Package includes Evidence Manifest",
       "OrcaReportPackage", "OrcaEvidenceItem", "MANY_TO_MANY",
       "Manifest entries reference approved evidence by metadata + SHA-256 (no raw bytes)."),
    _l("reviewDecisionAppliesToObservation", "Review Decision applies to Observation",
       "OrcaReviewDecision", "OrcaObservation", "MANY_TO_ONE", "ReviewDecision over an observation."),
    _l("reviewDecisionAppliesToEvidenceItem", "Review Decision applies to Evidence Item",
       "OrcaReviewDecision", "OrcaEvidenceItem", "MANY_TO_ONE", "ReviewDecision over an evidence item."),
    _l("reviewDecisionAppliesToRelationship", "Review Decision applies to Relationship",
       "OrcaReviewDecision", "OrcaRelationship", "MANY_TO_ONE", "ReviewDecision over a relationship."),
    _l("auditEventRecordsActionOnObject", "Audit Event records action on object",
       "OrcaAuditEvent", "OrcaCase", "MANY_TO_ONE",
       "AuditEvent.target_type/target_id — append-only record of a consequential action."),
)
