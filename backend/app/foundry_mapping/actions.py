"""ORCA → Foundry action-type mappings (v0.9).

Every action mirrors an existing, audited ORCA workflow and carries the same RBAC + case
membership gate. The ``required_case_role`` token is one of: ``""`` (global only),
``member`` (any active member), ``mutating`` (case_manager/analyst/reviewer), ``reviewer``
(reviewer only), or ``case_manager``. No action is autonomous — assistive/AIP proposals
route through the review queue (``propose_only``). The ``FORBIDDEN_WORKFLOWS`` list is the
set of behaviours that must never be expressed as an action type.
"""

from __future__ import annotations

from app.foundry_mapping.types import FoundryActionType

# Behaviours that must NEVER be mapped to a Foundry action (validated by tests).
FORBIDDEN_WORKFLOWS: tuple[str, ...] = (
    "scraping",
    "dark_web_collection",
    "autonomous_hunting",
    "face_search",
    "offender_targeting",
    "victim_targeting",
    "external_osint_integration",
    "palantir_live_sync",
    "palantir_production_write",
    "aip_automation",
    "bulk_social_monitoring",
    "direct_contact",
)

# ORCA invariants the mapping preserves end to end.
INVARIANTS: tuple[str, ...] = (
    "AI proposes, analysts decide",
    "Relationships require approved supporting observations",
    "Reports cite approved evidence only",
    "Evidence is case-scoped and hash-verifiable",
    "Graph traversal uses approved relationships only",
    "Case membership enforces need-to-know access",
    "Partner export viewers receive approved report packages only",
    "Privileged actions are audited",
    "No CSAM storage or handling",
)


def _a(
    api_name, title, endpoint, affected, capability, case_role, audit, invariant,
    *, propose_only=False, description="",
) -> FoundryActionType:
    return FoundryActionType(
        api_name=api_name, title=title, orca_endpoint=endpoint, affected_object=affected,
        required_capability=capability, required_case_role=case_role, writes_audit=audit,
        preserves_invariant=invariant, propose_only=propose_only, description=description,
    )


ACTION_TYPES: tuple[FoundryActionType, ...] = (
    _a("createCase", "Create case", "POST /cases", "OrcaCase", "create_case", "",
       True, "Case membership enforces need-to-know access",
       description="Creator is auto-enrolled as the case manager."),
    _a("assignCaseMember", "Assign case member", "POST /cases/{id}/members", "OrcaCaseMembership",
       "", "case_manager", True, "Case membership enforces need-to-know access"),
    _a("revokeCaseMember", "Revoke case member", "DELETE /cases/{id}/members/{membershipId}",
       "OrcaCaseMembership", "", "case_manager", True,
       "Case membership enforces need-to-know access"),
    _a("createSource", "Create source", "POST /observations (inline) or /sources", "OrcaSource",
       "create_observation", "mutating", False, "Evidence is case-scoped and hash-verifiable",
       description="Source provenance is captured at intake."),
    _a("createObservation", "Create observation", "POST /observations", "OrcaObservation",
       "create_observation", "mutating", True, "AI proposes, analysts decide",
       description="Enters the review queue as proposed; never auto-approved."),
    _a("createEvidenceItem", "Create evidence item", "POST /evidence", "OrcaEvidenceItem",
       "create_evidence", "mutating", True, "Evidence is case-scoped and hash-verifiable"),
    _a("uploadEvidenceFileMetadata", "Upload evidence file", "POST /cases/{id}/evidence/upload",
       "OrcaEvidenceItem", "create_evidence", "mutating", True,
       "Evidence is case-scoped and hash-verifiable",
       description="Safe-by-default policy: reject executables, quarantine unknown types."),
    _a("verifyEvidenceHash", "Verify evidence hash", "POST /evidence/{id}/verify",
       "OrcaEvidenceItem", "read_case_material", "member", True,
       "Evidence is case-scoped and hash-verifiable"),
    _a("approveObservation", "Approve observation", "POST /review/{id}/decision", "OrcaReviewDecision",
       "review_decide", "reviewer", True, "AI proposes, analysts decide",
       description="No self-review without an audited admin override."),
    _a("rejectObservation", "Reject observation", "POST /review/{id}/decision", "OrcaReviewDecision",
       "review_decide", "reviewer", True, "AI proposes, analysts decide"),
    _a("markObservationNeedsMoreReview", "Mark observation needs more review",
       "POST /review/{id}/decision", "OrcaReviewDecision", "review_decide", "reviewer", True,
       "AI proposes, analysts decide"),
    _a("approveEvidence", "Approve evidence", "POST /evidence/{id}/decision", "OrcaEvidenceItem",
       "review_decide", "reviewer", True, "AI proposes, analysts decide"),
    _a("rejectEvidence", "Reject evidence", "POST /evidence/{id}/decision", "OrcaEvidenceItem",
       "review_decide", "reviewer", True, "AI proposes, analysts decide"),
    _a("quarantineEvidence", "Quarantine evidence", "POST /evidence/{id}/decision", "OrcaEvidenceItem",
       "review_decide", "reviewer", True, "No CSAM storage or handling",
       description="Isolates material pending a handling decision; excluded from reports."),
    _a("createRelationshipFromApprovedObservation", "Create relationship from approved observation",
       "POST /relationships", "OrcaRelationship", "create_relationship", "mutating", True,
       "Relationships require approved supporting observations"),
    _a("generateReportDraft", "Generate report draft", "POST /cases/{id}/report", "OrcaReport",
       "generate_report", "mutating", True, "Reports cite approved evidence only"),
    _a("generateReportPackage", "Generate report package", "POST /cases/{id}/report/package",
       "OrcaReportPackage", "generate_report", "mutating", True,
       "Partner export viewers receive approved report packages only",
       description="Approved material only; raw evidence bytes are never bundled."),
    _a("downloadReportPackage", "Download report package", "GET /report-packages/{id}/package",
       "OrcaReportPackage", "view_approved_reports", "member", True,
       "Partner export viewers receive approved report packages only"),
    _a("closeCase", "Close case", "PATCH /cases/{id} (status=closed)", "OrcaCase",
       "manage_case", "case_manager", True, "Privileged actions are audited",
       description="Planned ORCA endpoint; lifecycle status change."),
    _a("archiveCase", "Archive case", "PATCH /cases/{id} (status=archived)", "OrcaCase",
       "manage_case", "case_manager", True, "Privileged actions are audited",
       description="Planned ORCA endpoint; lifecycle status change."),
)
