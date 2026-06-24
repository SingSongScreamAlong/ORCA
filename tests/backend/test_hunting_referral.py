"""Hunting Grounds → LE referral dossier.

The "locate → case" output: given a monitored source, ORCA aggregates the located identifiers,
the text leads, and the relationship map — with provenance and lawful basis — into a package an
analyst can hand to law enforcement. Pointers and metadata only; no media.
"""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed #RI-2026-06",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _monitored(client, name="RI listings", url="https://ri.invalid/x"):
    sid = client.post(
        SRC,
        json={"name": name, "url": url, "category": "escort_listing", "aor": "Rhode Island"},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def test_referral_aggregates_located_identifiers_and_provenance(client):
    sid = _monitored(client)
    # Two text leads that locate identifiers (auto-extracted from the text).
    client.post(
        f"{SRC}/{sid}/leads",
        json={"summary": "ad: call 401-555-0142, email vip@mail.invalid", "confidence": 0.5},
        headers=ANA,
    )
    client.post(
        f"{SRC}/{sid}/leads",
        json={"summary": "second ad reuses 401.555.0142 and @sky", "confidence": 0.4},
        headers=ANA,
    )

    pkg = client.get(f"{SRC}/{sid}/referral", headers=ANA)
    assert pkg.status_code == 200, pkg.text
    body = pkg.json()

    # Provenance + lawful basis travel with the dossier.
    assert body["source"]["name"] == "RI listings"
    assert body["source"]["lawful_basis"] == AUTH["lawful_basis"]
    assert body["source"]["authorized_by"] == "admin"

    # Located identifiers, deduped across both leads (the phone appears in both).
    located = {(i["entity_type"], i["value"]) for i in body["located_identifiers"]}
    assert ("phone_number", "+14015550142") in located
    assert ("email", "vip@mail.invalid") in located
    assert ("username", "sky") in located
    assert body["observation_count"] == 2
    assert body["identifier_count"] == len(located)
    # No-media notice + a renderable markdown dossier.
    assert "no media" in body["notice"].lower()
    assert body["summary_markdown"].startswith("# Referral dossier")
    assert "+14015550142" in body["summary_markdown"]


def test_referral_includes_relationships_between_identifiers(client):
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from app.models.enums import Origin, RelationshipType, ReviewStatus
    from app.repositories.uow import build_unit_of_work
    from app.schemas.relationship import RelationshipRead

    sid = _monitored(client)
    obs = client.post(
        f"{SRC}/{sid}/leads",
        json={
            "summary": "ad with two numbers",
            "confidence": 0.5,
            "entities": [
                {"entity_type": "phone_number", "value": "+14015550001"},
                {"entity_type": "phone_number", "value": "+14015550002"},
            ],
        },
        headers=ANA,
    ).json()
    a, b = (UUID(e) for e in obs["entity_ids"])
    # A relationship linking the two located numbers (inserted directly — the relationship API's
    # approved-observation rules are out of scope for this test).
    now = datetime.now(UTC)
    uow = build_unit_of_work()
    uow.relationships.add(
        RelationshipRead(
            id=uuid4(), case_id=None, source_entity_id=a, target_entity_id=b,
            relationship_type=RelationshipType.SHARED_ACCOUNT, confidence=0.6,
            origin=Origin.ANALYST_CREATED, status=ReviewStatus.APPROVED,
            observation_ids=[], created_at=now, updated_at=now,
        )
    )
    uow.commit()

    body = client.get(f"{SRC}/{sid}/referral", headers=ANA).json()
    rels = body["relationships"]
    assert any(r["relationship_type"] == "shared_account" for r in rels), rels
    values = {r["source_value"] for r in rels} | {r["target_value"] for r in rels}
    assert {"+14015550001", "+14015550002"} <= values


def test_referral_empty_for_source_with_no_leads(client):
    sid = _monitored(client)
    body = client.get(f"{SRC}/{sid}/referral", headers=ANA).json()
    assert body["observation_count"] == 0
    assert body["located_identifiers"] == []
    assert "(none located yet)" in body["summary_markdown"]


def test_referral_is_audited(client):
    sid = _monitored(client)
    client.get(f"{SRC}/{sid}/referral", headers=ANA)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.referral", headers=ADMIN).json()
    assert any(e["action"] == "hunting.referral.generated" for e in entries)


def test_referral_requires_read_capability(client):
    sid = _monitored(client)
    # Partners/viewers without READ_CASE_MATERIAL can't pull a referral... but viewers CAN read.
    # 'partner' (partner_export_viewer) lacks READ_CASE_MATERIAL → 403.
    assert client.get(f"{SRC}/{sid}/referral", headers={"X-ORCA-User": "partner"}).status_code == 403


# --- per-identifier referral (the cross-venue case file for one identifier) ------

IDREF = f"{PREFIX}/hunting/intel/identifier/referral"


def _monitored_in(client, name, url, aor):
    sid = client.post(
        SRC,
        json={"name": name, "url": url, "category": "escort_listing", "aor": aor},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def test_identifier_referral_assembles_cross_venue_case_file(client):
    a = _monitored_in(client, "RI listings", "https://ri.invalid/x", "Rhode Island")
    b = _monitored_in(client, "CT listings", "https://ct.invalid/y", "Connecticut")
    client.post(
        f"{SRC}/{a}/leads",
        json={"summary": "ad: call 401-555-0142, ask for @sky", "confidence": 0.5},
        headers=ANA,
    )
    client.post(
        f"{SRC}/{b}/leads",
        json={"summary": "repost 401.555.0142, bitcoin only", "confidence": 0.4},
        headers=ANA,
    )

    res = client.get(IDREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["venue_count"] == 2
    assert body["lead_count"] == 2
    assert sorted(body["aors"]) == ["Connecticut", "Rhode Island"]
    # Every venue's provenance + lawful basis travels with the dossier.
    assert {s["name"] for s in body["sources"]} == {"RI listings", "CT listings"}
    assert all(s["lawful_basis"] == AUTH["lawful_basis"] for s in body["sources"])
    # The co-occurring handle is surfaced as a link candidate.
    assert ("username", "sky") in {(c["entity_type"], c["value"]) for c in body["co_occurring"]}
    # Renderable, no-media dossier (the package carries no media field, by construction).
    assert body["summary_markdown"].startswith("# Referral dossier — identifier +14015550142")
    assert "no media" in body["notice"].lower()
    assert "media" not in body


def test_identifier_referral_404_for_unlocated(client):
    _monitored_in(client, "Solo", "https://solo.invalid", "Rhode Island")
    res = client.get(IDREF, params={"type": "phone_number", "value": "+19998887777"}, headers=ANA)
    assert res.status_code == 404


def test_identifier_referral_is_audited(client):
    a = _monitored_in(client, "RI", "https://ri.invalid/z", "Rhode Island")
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142", "confidence": 0.5}, headers=ANA)
    client.get(IDREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    entries = client.get(
        f"{PREFIX}/audit?action_prefix=hunting.referral.identifier", headers=ADMIN
    ).json()
    assert any(e["action"] == "hunting.referral.identifier_generated" for e in entries)


def test_identifier_referral_requires_read_capability(client):
    a = _monitored_in(client, "RI", "https://ri.invalid/w", "Rhode Island")
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142", "confidence": 0.5}, headers=ANA)
    res = client.get(
        IDREF,
        params={"type": "phone_number", "value": "+14015550142"},
        headers={"X-ORCA-User": "partner"},
    )
    assert res.status_code == 403


# --- AOR operation rollup (the regional case file) ------------------------------

AORREF = f"{PREFIX}/hunting/intel/aor/referral"


def test_aor_rollup_consolidates_venues_identifiers_and_cross_venue_links(client):
    a = _monitored_in(client, "RI A", "https://ri-a.invalid", "Rhode Island")
    b = _monitored_in(client, "RI B", "https://ri-b.invalid", "Rhode Island")
    c = _monitored_in(client, "CT A", "https://ct-a.invalid", "Connecticut")  # out of scope
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142, @sky", "confidence": 0.5}, headers=ANA)
    client.post(f"{SRC}/{b}/leads", json={"summary": "same 401.555.0142, email vip@m.invalid", "confidence": 0.4}, headers=ANA)
    client.post(f"{SRC}/{c}/leads", json={"summary": "ct only 860-555-0000", "confidence": 0.4}, headers=ANA)

    res = client.get(AORREF, params={"aor": "Rhode Island"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    # Scoped to the AOR: only the two RI venues, not the CT one.
    assert body["source_count"] == 2
    assert {s["name"] for s in body["sources"]} == {"RI A", "RI B"}
    assert all(s["lawful_basis"] == AUTH["lawful_basis"] for s in body["sources"])
    # The shared phone is a cross-venue link (2 RI venues); the CT number is not present.
    cross = {i["value"] for i in body["cross_venue"]}
    assert "+14015550142" in cross
    assert "+18605550000" not in {i["value"] for i in body["located_identifiers"]}
    assert body["cross_venue_count"] == 1
    # Renderable, no-media operation dossier.
    assert body["summary_markdown"].startswith("# Operation rollup — Rhode Island")
    assert "no media" in body["notice"].lower()
    assert "media" not in body


def test_aor_rollup_empty_for_aor_with_no_monitored_sources(client):
    body = client.get(AORREF, params={"aor": "Nowhere"}, headers=ANA).json()
    assert body["source_count"] == 0
    assert body["located_identifiers"] == []
    assert "(none monitored in this AOR)" in body["summary_markdown"]


def test_aor_rollup_is_audited(client):
    _monitored_in(client, "RI", "https://ri.invalid/r", "Rhode Island")
    client.get(AORREF, params={"aor": "Rhode Island"}, headers=ANA)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.referral.aor", headers=ADMIN).json()
    assert any(e["action"] == "hunting.referral.aor_generated" for e in entries)


def test_aor_rollup_requires_read_capability(client):
    _monitored_in(client, "RI", "https://ri.invalid/p", "Rhode Island")
    res = client.get(AORREF, params={"aor": "Rhode Island"}, headers={"X-ORCA-User": "partner"})
    assert res.status_code == 403


# --- operation referral (the linked-network case file) --------------------------

OPREF = f"{PREFIX}/hunting/intel/operation/referral"


def test_operation_referral_wraps_the_linked_network(client):
    a = _monitored_in(client, "V1", "https://v1.invalid", "Rhode Island")
    b = _monitored_in(client, "V2", "https://v2.invalid", "Connecticut")
    # P co-occurs with @alpha (V1); @alpha co-occurs with an email (V2) → one operation, two AORs.
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142, @alpha", "confidence": 0.5}, headers=ANA)
    client.post(f"{SRC}/{b}/leads", json={"summary": "@alpha at boss@mail.invalid", "confidence": 0.4}, headers=ANA)

    res = client.get(OPREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["identifier_count"] == 3  # phone, @alpha, email
    assert sorted(body["aors"]) == ["Connecticut", "Rhode Island"]
    member_values = {m["value"] for m in body["members"]}
    assert {"+14015550142", "alpha", "boss@mail.invalid"} <= member_values
    # Each venue carries its lawful basis; the dossier is renderable and media-free.
    assert {s["name"] for s in body["venues"]} == {"V1", "V2"}
    assert all(s["lawful_basis"] == AUTH["lawful_basis"] for s in body["venues"])
    assert body["summary_markdown"].startswith("# Operation dossier — seed +14015550142")
    assert "no media" in body["notice"].lower()
    assert "media" not in body


def test_operation_referral_404_for_unlocated(client):
    _monitored_in(client, "Solo", "https://solo.invalid", "Rhode Island")
    res = client.get(OPREF, params={"type": "phone_number", "value": "+19998887777"}, headers=ANA)
    assert res.status_code == 404


def test_operation_referral_is_audited(client):
    a = _monitored_in(client, "RI", "https://ri.invalid/o", "Rhode Island")
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142", "confidence": 0.5}, headers=ANA)
    client.get(OPREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    entries = client.get(
        f"{PREFIX}/audit?action_prefix=hunting.referral.operation", headers=ADMIN
    ).json()
    assert any(e["action"] == "hunting.referral.operation_generated" for e in entries)


def test_operation_referral_requires_read_capability(client):
    a = _monitored_in(client, "RI", "https://ri.invalid/q", "Rhode Island")
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142", "confidence": 0.5}, headers=ANA)
    res = client.get(
        OPREF,
        params={"type": "phone_number", "value": "+14015550142"},
        headers={"X-ORCA-User": "partner"},
    )
    assert res.status_code == 403


# --- referral history (accountability over the four tiers) ----------------------

HIST = f"{PREFIX}/hunting/referrals"


def test_referral_history_records_every_tier(client):
    a = _monitored_in(client, "RI listings", "https://ri.invalid/h", "Rhode Island")
    client.post(f"{SRC}/{a}/leads", json={"summary": "call 401-555-0142", "confidence": 0.5}, headers=ANA)
    # Generate one referral of each scope.
    client.get(f"{SRC}/{a}/referral", headers=ANA)  # source
    client.get(IDREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)  # identifier
    client.get(AORREF, params={"aor": "Rhode Island"}, headers=ANA)  # aor
    client.get(OPREF, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)  # operation

    res = client.get(HIST, headers=ANA)
    assert res.status_code == 200, res.text
    history = res.json()
    # Newest-first: the referrals were generated source → identifier → aor → operation.
    assert [r["tier"] for r in history] == ["operation", "aor", "identifier", "source"]
    # Attributed, with a human-readable subject + count summary (no dossier contents).
    assert all(r["generated_by"] == "ana" and r["summary"] for r in history)
    by_tier = {r["tier"]: r for r in history}
    assert by_tier["source"]["target"] == "RI listings"
    assert "+14015550142" in by_tier["identifier"]["target"]
    assert by_tier["aor"]["target"] == "Rhode Island"
    assert "+14015550142" in by_tier["operation"]["target"]


def test_referral_history_empty_when_nothing_referred(client):
    assert client.get(HIST, headers=ANA).json() == []


def test_referral_history_requires_read_capability(client):
    assert client.get(HIST, headers={"X-ORCA-User": "partner"}).status_code == 403
