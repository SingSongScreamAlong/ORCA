"""Hunting Grounds — AOR intelligence (cross-venue link analysis).

The analytical payoff: when the same located identifier (a phone, wallet, handle, .onion) recurs
across two or more monitored venues, that's a cross-venue link — the strongest case-building lead.
These tests prove the picture surfaces it, scopes by AOR, and that the LE referral is enriched
with the cross-venue count. Read-only; pointers/metadata only.
"""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
INTEL = f"{PREFIX}/hunting/intel"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _monitored(client, name, url, aor="Rhode Island"):
    sid = client.post(
        SRC,
        json={"name": name, "url": url, "category": "escort_listing", "aor": aor},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def _lead(client, sid, summary):
    return client.post(f"{SRC}/{sid}/leads", json={"summary": summary, "confidence": 0.4}, headers=ANA)


# --- cross-venue detection ------------------------------------------------------


def test_shared_phone_across_two_venues_is_cross_venue(client):
    a = _monitored(client, "Venue A", "https://a.invalid")
    b = _monitored(client, "Venue B", "https://b.invalid")
    _lead(client, a, "Ad: call +1 401 555 0142 now")
    _lead(client, b, "Different post, same number 401-555-0142, ask for @sky")

    pic = client.get(INTEL, headers=ANA).json()
    assert pic["monitored_sources"] == 2
    assert pic["leads"] == 2
    cross = {(i["entity_type"], i["value"]): i for i in pic["cross_venue"]}
    # The shared phone links both venues; the @sky handle (only venue B) does not.
    assert ("phone_number", "+14015550142") in cross
    shared = cross[("phone_number", "+14015550142")]
    assert shared["source_count"] == 2
    assert set(shared["sources"]) == {"Venue A", "Venue B"}
    assert ("username", "sky") not in cross  # single-venue → not cross-venue
    assert pic["cross_venue_count"] == 1


def test_single_venue_identifier_not_cross_venue(client):
    a = _monitored(client, "Solo", "https://solo.invalid")
    _lead(client, a, "only here: vip@host.invalid")
    pic = client.get(INTEL, headers=ANA).json()
    assert pic["cross_venue"] == []
    assert any(i["value"] == "vip@host.invalid" for i in pic["top_identifiers"])


def test_intel_scopes_by_aor(client):
    a = _monitored(client, "RI A", "https://ri-a.invalid", aor="Rhode Island")
    b = _monitored(client, "RI B", "https://ri-b.invalid", aor="Rhode Island")
    c = _monitored(client, "CT A", "https://ct-a.invalid", aor="Connecticut")
    _lead(client, a, "call 401-555-0142")
    _lead(client, b, "call 401-555-0142")
    _lead(client, c, "call 401-555-0142")

    ri = client.get(f"{INTEL}?aor=Rhode%20Island", headers=ANA).json()
    assert ri["monitored_sources"] == 2
    # Scoped to RI: the phone appears in 2 RI venues (CT's lead is out of scope).
    phone = next(i for i in ri["cross_venue"] if i["value"] == "+14015550142")
    assert phone["source_count"] == 2

    all_aors = client.get(INTEL, headers=ANA).json()
    phone_all = next(i for i in all_aors["cross_venue"] if i["value"] == "+14015550142")
    assert phone_all["source_count"] == 3  # all three venues


def test_intel_empty_when_no_monitored_sources(client):
    pic = client.get(INTEL, headers=ANA).json()
    assert pic["monitored_sources"] == 0
    assert pic["cross_venue"] == [] and pic["top_identifiers"] == []


# --- referral is enriched with the cross-venue count ----------------------------


def test_referral_marks_cross_venue_identifiers(client):
    a = _monitored(client, "Venue A", "https://a.invalid")
    b = _monitored(client, "Venue B", "https://b.invalid")
    _lead(client, a, "call +1 401 555 0142, email a@host.invalid")
    _lead(client, b, "same number 401.555.0142")

    pkg = client.get(f"{SRC}/{a}/referral", headers=ANA).json()
    by_value = {i["value"]: i for i in pkg["located_identifiers"]}
    # The shared phone is flagged cross-venue (2); the email (only venue A) is single (1).
    assert by_value["+14015550142"]["venue_count"] == 2
    assert by_value["a@host.invalid"]["venue_count"] == 1
    assert "cross-venue: 2 venues" in pkg["summary_markdown"]


# --- identifier pivot / dossier -------------------------------------------------

DOSSIER = f"{INTEL}/identifier"


def test_identifier_dossier_pivots_across_venues_and_aors(client):
    a = _monitored(client, "RI A", "https://ri-a.invalid", aor="Rhode Island")
    b = _monitored(client, "CT B", "https://ct-b.invalid", aor="Connecticut")
    _lead(client, a, "Ad: call +1 401 555 0142, ask for @sky")
    _lead(client, b, "Repost: 401-555-0142 available, bitcoin only")

    res = client.get(DOSSIER, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["venue_count"] == 2
    assert body["lead_count"] == 2
    assert sorted(body["aors"]) == ["Connecticut", "Rhode Island"]
    # Every sighting points back to its venue and AOR (pointer/metadata only — no media field).
    venues = {(ap["source_name"], ap["aor"]) for ap in body["appearances"]}
    assert venues == {("RI A", "Rhode Island"), ("CT B", "Connecticut")}
    assert all("observation_id" in ap and "media" not in ap for ap in body["appearances"])
    # The handle co-occurs with the phone in venue A's lead — a link candidate.
    co = {(c["entity_type"], c["value"]): c["shared_leads"] for c in body["co_occurring"]}
    assert co[("username", "sky")] == 1


def test_identifier_dossier_404_for_unlocated_identifier(client):
    _monitored(client, "Solo", "https://solo.invalid")
    res = client.get(DOSSIER, params={"type": "phone_number", "value": "+19998887777"}, headers=ANA)
    assert res.status_code == 404


def test_identifier_dossier_scoped_to_monitored_leads(client):
    # An identifier located only from a single venue still pivots — venue_count 1, that one AOR,
    # no co-occurring identifiers when it's alone in the lead.
    a = _monitored(client, "Solo", "https://solo.invalid", aor="Rhode Island")
    _lead(client, a, "lone wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    res = client.get(
        DOSSIER,
        params={"type": "crypto_address", "value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
        headers=ANA,
    ).json()
    assert res["venue_count"] == 1
    assert res["aors"] == ["Rhode Island"]
    assert res["co_occurring"] == []


# --- operation cluster (connected-component network) ----------------------------

OP = f"{INTEL}/operation"


def test_operation_cluster_is_the_transitive_network(client):
    a = _monitored(client, "V1", "https://v1.invalid")
    b = _monitored(client, "V2", "https://v2.invalid")
    c = _monitored(client, "V3", "https://v3.invalid")
    # P co-occurs with @alpha (V1); @alpha co-occurs with an email (V2) → P—alpha—email is one
    # operation, reached transitively from P even though P and the email never share a lead.
    _lead(client, a, "call +1 401 555 0142, ask for @alpha")
    _lead(client, b, "@alpha also at boss@mail.invalid")
    _lead(client, c, "different crew: 860-555-0000")  # unrelated operation

    res = client.get(OP, params={"type": "phone_number", "value": "+14015550142"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    members = {(m["entity_type"], m["value"]) for m in body["members"]}
    assert ("phone_number", "+14015550142") in members  # seed
    assert ("username", "alpha") in members  # 1 hop (shared lead in V1)
    assert ("email", "boss@mail.invalid") in members  # 2 hops (alpha→email in V2)
    assert ("phone_number", "+18605550000") not in members  # unrelated operation excluded
    assert body["identifier_count"] == 3
    assert body["venue_count"] == 2  # V1 + V2, not V3
    assert body["truncated"] is False
    assert "media" not in body


def test_operation_cluster_isolates_unconnected_identifiers(client):
    c = _monitored(client, "Solo", "https://solo.invalid")
    _lead(client, c, "lone wallet 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    res = client.get(
        OP,
        params={"type": "crypto_address", "value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
        headers=ANA,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["identifier_count"] == 1
    assert body["venue_count"] == 1


def test_operation_cluster_links_via_relationship_edge(client):
    # Two identifiers that never co-occur become one operation when a relationship ties them.
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from app.models.enums import Origin, RelationshipType, ReviewStatus
    from app.repositories.uow import build_unit_of_work
    from app.schemas.relationship import RelationshipRead

    a = _monitored(client, "V1", "https://v1.invalid")
    b = _monitored(client, "V2", "https://v2.invalid")
    o1 = _lead(client, a, "phone 401-555-1111").json()
    o2 = _lead(client, b, "phone 401-555-2222").json()
    e1, e2 = UUID(o1["entity_ids"][0]), UUID(o2["entity_ids"][0])
    now = datetime.now(UTC)
    uow = build_unit_of_work()
    uow.relationships.add(
        RelationshipRead(
            id=uuid4(), case_id=None, source_entity_id=e1, target_entity_id=e2,
            relationship_type=RelationshipType.SHARED_ACCOUNT, confidence=0.7,
            origin=Origin.ANALYST_CREATED, status=ReviewStatus.APPROVED,
            observation_ids=[], created_at=now, updated_at=now,
        )
    )
    uow.commit()

    res = client.get(OP, params={"type": "phone_number", "value": "+14015551111"}, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    assert {"+14015551111", "+14015552222"} <= {m["value"] for m in body["members"]}
    assert body["identifier_count"] == 2
    assert any(r["relationship_type"] == "shared_account" for r in body["relationships"])


def test_operation_cluster_404_for_unlocated(client):
    _monitored(client, "Solo", "https://solo.invalid")
    res = client.get(OP, params={"type": "phone_number", "value": "+19998887777"}, headers=ANA)
    assert res.status_code == 404
