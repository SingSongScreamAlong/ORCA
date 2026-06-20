"""Analyst Copilot (v1.0) — propose-only AI assistance.

Proves the safety contract:

* the Copilot reasons over approved material only (proposed/rejected excluded)
* suggestions are proposed only — they never create approved entities/relationships
* every result carries generated_by_ai + requires_human_review metadata
* the citation checker flags unsupported claims
* partner export viewers cannot reach the Copilot; unassigned users get 403
* requests are audited; the mock provider is deterministic
"""

from __future__ import annotations

from datetime import UTC, datetime

PREFIX = "/api/v1"
FORBIDDEN = "You do not have access to this case."

AI = [
    "summarize", "extract-entities", "suggest-relationships",
    "draft-report-section", "check-citations", "timeline-summary",
]


def H(user: str) -> dict:
    return {"X-ORCA-User": user}


def _seed_case(client) -> str:
    return client.get(f"{PREFIX}/cases", headers=H("admin")).json()[0]["id"]


def _source(client) -> str:
    return client.get(f"{PREFIX}/sources", headers=H("admin")).json()[0]["id"]


def _fresh_case(client) -> str:
    cid = client.post(
        f"{PREFIX}/cases", json={"title": "Copilot case", "owner": "admin"}, headers=H("admin")
    ).json()["id"]
    for user, role in (("ana", "analyst"), ("rae", "reviewer")):
        client.post(
            f"{PREFIX}/cases/{cid}/members", json={"username": user, "case_role": role}, headers=H("admin")
        )
    return cid


def _entity(client, etype, value) -> str:
    return client.post(
        f"{PREFIX}/entities", json={"entity_type": etype, "value": value}, headers=H("ana")
    ).json()["id"]


def _intake(client, case_id, src, note, entity_ids):
    return client.post(
        f"{PREFIX}/observations",
        json={
            "case_id": case_id, "timestamp": datetime.now(UTC).isoformat(), "source_id": src,
            "collector": "ana", "notes": note, "confidence": 0.7, "entity_ids": entity_ids,
        },
        headers=H("ana"),
    ).json()


def _approved_obs(client, case_id, src, note, entity_ids=None):
    obs = _intake(client, case_id, src, note, entity_ids or [])
    item = next(
        i for i in client.get(f"{PREFIX}/review", headers=H("admin")).json()
        if i["subject_id"] == obs["id"]
    )
    client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=H("rae"))
    return obs["id"]


def _ai(client, case_id, kind, user="ana", body=None):
    return client.post(f"{PREFIX}/cases/{case_id}/ai/{kind}", json=body or {}, headers=H(user))


# --- approved-only --------------------------------------------------------------


def test_summarize_uses_approved_material_only(client):
    case_id, src = _fresh_case(client), _source(client)
    _approved_obs(client, case_id, src, "APPROVED-NOTE")
    _intake(client, case_id, src, "PROPOSED-NOTE", [])  # left proposed

    result = _ai(client, case_id, "summarize").json()
    assert "1 approved observation(s)" in result["summary"]
    # Only the approved observation is listed as source material.
    assert len(result["meta"]["source_material_ids"]) == 1


def test_draft_report_uses_approved_observations_only(client):
    case_id, src = _fresh_case(client), _source(client)
    _approved_obs(client, case_id, src, "DRAFT-APPROVED")
    _intake(client, case_id, src, "DRAFT-PROPOSED", [])

    result = _ai(client, case_id, "draft-report-section", body={"section_title": "Findings"}).json()
    md = result["report_draft"]["draft_markdown"]
    assert "DRAFT-APPROVED" in md
    assert "DRAFT-PROPOSED" not in md
    assert len(result["report_draft"]["cited_observation_ids"]) == 1


# --- proposed-only outputs ------------------------------------------------------


def test_entity_extraction_is_proposed_only(client):
    case_id = _fresh_case(client)
    result = _ai(
        client, case_id, "extract-entities",
        body={"note": "Call +15555551234 about 'Jaye' and @jaye_listings."},
    ).json()
    values = {e["value"] for e in result["proposed_entities"]}
    assert any("5555551234" in v for v in values)
    assert "Jaye" in values
    assert "jaye_listings" in values
    assert result["meta"]["status"] == "proposed"
    assert result["meta"]["requires_human_review"] is True


def test_relationship_suggestions_do_not_create_approved_relationships(client):
    case_id, src = _fresh_case(client), _source(client)
    a, b = _entity(client, "alias", "Alpha"), _entity(client, "username", "bravo")
    _approved_obs(client, case_id, src, "co-occurrence", [a, b])

    result = _ai(client, case_id, "suggest-relationships").json()
    assert result["proposed_relationships"], "expected a candidate from co-occurrence"
    assert all(r["relationship_type"] == "appears_with" for r in result["proposed_relationships"])
    # Nothing was actually created — the case still has no relationships.
    rels = client.get(f"{PREFIX}/cases/{case_id}/relationships", headers=H("ana")).json()
    assert rels == []


def test_citation_checker_flags_unsupported_claims(client):
    case_id = _seed_case(client)
    result = _ai(
        client, case_id, "check-citations",
        body={"draft_text": "The suspect is guilty. This proves the connection. Evidence shows a link."},
        user="ana",
    ).json()
    assert result["unsupported_claims"], "assertive claim should be flagged"
    claims = " ".join(c["claim"].lower() for c in result["unsupported_claims"])
    assert "guilty" in claims or "proves" in claims
    assert any(g["issue"] == "missing_citation" for g in result["citation_gaps"])


# --- metadata + determinism -----------------------------------------------------


def test_all_outputs_carry_ai_metadata(client):
    case_id = _seed_case(client)
    for kind in AI:
        result = _ai(client, case_id, kind).json()
        meta = result["meta"]
        assert meta["generated_by_ai"] is True, kind
        assert meta["requires_human_review"] is True, kind
        assert meta["status"] == "proposed", kind
        assert meta["provider"] == "mock", kind
        assert meta["generated_at"], kind


def test_mock_provider_is_deterministic(client):
    case_id, src = _fresh_case(client), _source(client)
    a, b = _entity(client, "alias", "Det"), _entity(client, "phone_number", "+15550001111")
    _approved_obs(client, case_id, src, "det note", [a, b])
    first = _ai(client, case_id, "suggest-relationships").json()["proposed_relationships"]
    second = _ai(client, case_id, "suggest-relationships").json()["proposed_relationships"]
    assert first == second
    s1 = _ai(client, case_id, "summarize").json()["summary"]
    s2 = _ai(client, case_id, "summarize").json()["summary"]
    assert s1 == s2


# --- access control -------------------------------------------------------------


def test_partner_cannot_access_copilot(client):
    case_id = _seed_case(client)  # partner is a member, but lacks read_case_material
    for kind in AI:
        assert _ai(client, case_id, kind, user="partner").status_code == 403, kind


def test_unassigned_user_is_forbidden(client):
    case_id = _seed_case(client)
    denied = _ai(client, case_id, "summarize", user="nomad")
    assert denied.status_code == 403
    assert denied.json()["detail"] == FORBIDDEN


def test_viewer_can_use_readonly_copilot(client):
    case_id = _seed_case(client)  # vic is a viewer member
    assert _ai(client, case_id, "summarize", user="vic").status_code == 200


# --- audit ----------------------------------------------------------------------


def test_copilot_requests_are_audited(client):
    case_id = _seed_case(client)
    _ai(client, case_id, "summarize")
    _ai(client, case_id, "suggest-relationships")
    actions = [e["action"] for e in client.get(f"{PREFIX}/cases/{case_id}/audit", headers=H("admin")).json()]
    assert "ai_assist.summarize" in actions
    assert "ai_assist.suggest_relationships" in actions
