"""ORCA → Palantir Foundry ontology mapping (v0.9).

Proves the mapping is complete, safe, and preserves ORCA's invariants:

* every core ORCA model has a Foundry object mapping
* every required relationship has a link mapping
* every required workflow has an action mapping, and no unsafe workflow is mapped
* partner export viewers get no raw evidence; viewers get no raw bytes
* reports/packages map approved material only; evidence carries SHA-256 + provenance
* audit events map to a Foundry-readable object
* the committed foundry/*.json export is in sync with the spec, and is deterministic
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.rbac import Capability
from app.foundry_mapping.actions import FORBIDDEN_WORKFLOWS, INVARIANTS
from app.foundry_mapping.export import export
from app.foundry_mapping.spec import build_spec
from app.foundry_mapping.types import to_dict

SPEC = build_spec()
_OBJECTS = {o.api_name: o for o in SPEC.objects}
_LINKS = {link.api_name for link in SPEC.links}
_ACTIONS = {a.api_name: a for a in SPEC.actions}
_PERMS = {p.case_role: p for p in SPEC.permissions}

REPO_ROOT = Path(__file__).resolve().parents[2]
FOUNDRY_DIR = REPO_ROOT / "foundry"

_ALLOWED_CASE_ROLE_TOKENS = {"", "member", "mutating", "reviewer", "case_manager"}


# --- object coverage ------------------------------------------------------------


def test_all_required_object_types_present():
    required = {
        "OrcaCase", "OrcaUser", "OrcaCaseMembership", "OrcaSource", "OrcaObservation",
        "OrcaEvidenceItem", "OrcaEntity", "OrcaRelationship", "OrcaReviewDecision",
        "OrcaTask", "OrcaReport", "OrcaReportPackage", "OrcaAuditEvent",
    }
    assert required <= set(_OBJECTS)


def test_every_core_orca_model_is_mapped():
    # Each core ORCA schema/model is represented by some object type's orca_model.
    mapped = " ".join(o.orca_model for o in SPEC.objects)
    for model in (
        "CaseRead", "UserRead", "CaseMemberRead", "SourceRead", "ObservationRead",
        "EvidenceItemRead", "EntityRead", "RelationshipRead", "ReportRead",
        "ReportPackageRead", "ReviewItemRead", "AuditEntry",
    ):
        assert model in mapped, model


def test_object_primary_keys_are_real_properties():
    for o in SPEC.objects:
        names = {p.api_name for p in o.properties}
        assert o.primary_key in names, o.api_name


def test_every_property_has_a_mapping_kind():
    for o in SPEC.objects:
        for p in o.properties:
            assert p.mapping in {"direct", "derived", "planned"}, (o.api_name, p.api_name)
            # Direct properties must name a real ORCA field; derived/planned need not.
            if p.mapping == "direct":
                assert p.orca_field, (o.api_name, p.api_name)


# --- link coverage --------------------------------------------------------------


def test_all_required_link_types_present():
    required = {
        "caseContainsSource", "caseContainsObservation", "caseContainsEvidenceItem",
        "caseContainsEntity", "caseContainsRelationship", "caseContainsReport",
        "caseContainsReportPackage", "caseHasCaseMembership", "sourceSupportsObservation",
        "observationCitesEvidenceItem", "observationSupportsRelationship",
        "entityParticipatesInRelationship", "reportCitesObservation",
        "reportPackageIncludesReport", "reportPackageIncludesEvidenceManifest",
        "reviewDecisionAppliesToObservation", "reviewDecisionAppliesToEvidenceItem",
        "reviewDecisionAppliesToRelationship", "auditEventRecordsActionOnObject",
    }
    assert required <= _LINKS


def test_links_reference_known_objects():
    for link in SPEC.links:
        assert link.source_object in _OBJECTS, link.api_name
        assert link.target_object in _OBJECTS, link.api_name


# --- action coverage + safety ---------------------------------------------------


def test_all_required_action_types_present():
    required = {
        "createCase", "assignCaseMember", "revokeCaseMember", "createSource",
        "createObservation", "createEvidenceItem", "uploadEvidenceFileMetadata",
        "verifyEvidenceHash", "approveObservation", "rejectObservation",
        "markObservationNeedsMoreReview", "approveEvidence", "rejectEvidence",
        "quarantineEvidence", "createRelationshipFromApprovedObservation",
        "generateReportDraft", "generateReportPackage", "downloadReportPackage",
        "closeCase", "archiveCase",
    }
    assert required <= set(_ACTIONS)


def test_no_unsafe_workflow_is_mapped():
    blob = " ".join(
        f"{a.api_name} {a.orca_endpoint} {a.title} {a.description}".lower() for a in SPEC.actions
    )
    for forbidden in FORBIDDEN_WORKFLOWS:
        # The forbidden token must not appear as an action; it is only ever a documented
        # non-goal. (Tokens use underscores; also guard the despaced form.)
        assert forbidden not in {a.api_name for a in SPEC.actions}
        assert forbidden.replace("_", " ") not in blob
        assert forbidden not in blob


def test_actions_carry_real_capability_and_case_role_gates():
    valid_caps = {c.value for c in Capability} | {""}
    for a in SPEC.actions:
        assert a.required_capability in valid_caps, a.api_name
        assert a.required_case_role in _ALLOWED_CASE_ROLE_TOKENS, a.api_name
        assert a.preserves_invariant in INVARIANTS, a.api_name


def test_review_actions_are_reviewer_gated_and_audited():
    for name in ("approveObservation", "rejectObservation", "markObservationNeedsMoreReview",
                 "approveEvidence", "rejectEvidence", "quarantineEvidence"):
        a = _ACTIONS[name]
        assert a.required_capability == "review_decide"
        assert a.required_case_role == "reviewer"
        assert a.writes_audit is True


def test_membership_actions_are_case_manager_gated():
    for name in ("assignCaseMember", "revokeCaseMember"):
        assert _ACTIONS[name].required_case_role == "case_manager"
        assert _ACTIONS[name].writes_audit is True


def test_no_action_is_autonomous():
    # Nothing in the human-action set bypasses review; assistive proposals would be
    # propose_only and route through the queue.
    assert all(a.propose_only is False for a in SPEC.actions)


# --- invariant preservation -----------------------------------------------------


def test_partner_export_viewer_gets_no_raw_material():
    partner = _PERMS["partner_export_viewer"]
    assert partner.can_access_raw_evidence is False
    assert partner.can_read_material is False
    assert partner.can_mutate is False
    assert partner.can_view_audit is False
    assert partner.can_view_approved_reports is True


def test_viewer_gets_metadata_but_no_raw_bytes():
    viewer = _PERMS["viewer"]
    assert viewer.can_read_material is True
    assert viewer.can_access_raw_evidence is False
    assert viewer.can_mutate is False


def test_only_reviewer_can_review():
    assert _PERMS["reviewer"].can_review is True
    for role in ("case_manager", "analyst", "viewer", "partner_export_viewer"):
        assert _PERMS[role].can_review is False


def test_reports_and_packages_map_approved_material_only():
    # The generating actions preserve approved-only invariants.
    assert _ACTIONS["generateReportDraft"].preserves_invariant == "Reports cite approved evidence only"
    pkg = _ACTIONS["generateReportPackage"]
    assert "approved" in pkg.description.lower()
    assert "raw evidence" in pkg.description.lower()
    # The report→observation link is documented as approved-only.
    link = next(link for link in SPEC.links if link.api_name == "reportCitesObservation")
    assert "approved" in link.orca_basis.lower()
    # Relationship support links require approved observations.
    rel = next(link for link in SPEC.links if link.api_name == "observationSupportsRelationship")
    assert "approved" in rel.orca_basis.lower()


def test_evidence_mapping_carries_integrity_and_provenance():
    ev = _OBJECTS["OrcaEvidenceItem"]
    names = {p.api_name for p in ev.properties}
    for required in ("sha256", "sourceId", "handlingNotes", "legalFlags", "verificationStatus",
                     "mimeType", "sizeBytes", "originalFilename", "status"):
        assert required in names, required
    # Sensitive evidence properties must be flagged so partner exports can exclude them.
    sensitive = {p.api_name for p in ev.properties if p.sensitive}
    assert {"handlingNotes", "legalFlags", "storageUri"} <= sensitive


def test_audit_event_is_a_readable_object():
    audit = _OBJECTS["OrcaAuditEvent"]
    names = {p.api_name for p in audit.properties}
    assert {"actorId", "action", "targetType", "targetId", "createdAt"} <= names
    assert "auditEventRecordsActionOnObject" in _LINKS


def test_spec_lists_invariants_and_forbidden_workflows():
    assert "No CSAM storage or handling" in SPEC.invariants
    assert "AI proposes, analysts decide" in SPEC.invariants
    assert "palantir_live_sync" in SPEC.forbidden_workflows
    assert "scraping" in SPEC.forbidden_workflows


# --- export ---------------------------------------------------------------------


def test_committed_export_is_in_sync(tmp_path):
    # Re-exporting must reproduce the committed foundry/*.json byte-for-byte (deterministic).
    export(tmp_path)
    for name in ("object_types.json", "link_types.json", "action_types.json",
                 "permissions.json", "ontology_spec.json"):
        fresh = (tmp_path / name).read_text(encoding="utf-8")
        committed = (FOUNDRY_DIR / name).read_text(encoding="utf-8")
        assert fresh == committed, f"{name} is stale — run `python -m app.foundry_mapping.export`"


def test_export_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    export(a)
    export(b)
    spec_a = json.loads((a / "ontology_spec.json").read_text())
    spec_b = json.loads((b / "ontology_spec.json").read_text())
    assert spec_a == spec_b
    assert len(spec_a["objects"]) == len(SPEC.objects)
    assert to_dict(SPEC.objects[0])  # dataclass serialises
