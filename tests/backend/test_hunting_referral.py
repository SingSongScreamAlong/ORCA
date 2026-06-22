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
