"""Hunting Grounds — cross-venue link proposal (locate → review-ready case link).

When two located identifiers co-occur in APPROVED leads across two or more monitored venues, the
system proposes an `appears_with` relationship into the review queue. These tests prove the lawful
two-stage loop: leads are proposed, an analyst approves them, the system proposes the cross-venue
link, and an analyst decides on that too. Only approved observations are cited; existing links are
not re-proposed.
"""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
PROPOSE = f"{PREFIX}/hunting/links/propose"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _monitored(client, name, url):
    sid = client.post(
        SRC,
        json={"name": name, "url": url, "category": "escort_listing", "aor": "Rhode Island"},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def _lead(client, sid, summary):
    return client.post(
        f"{SRC}/{sid}/leads", json={"summary": summary, "confidence": 0.4}, headers=ANA
    ).json()["id"]


def _approve(client, obs_id):
    items = client.get(f"{PREFIX}/review?status=proposed", headers=ADMIN).json()
    item = next(i for i in items if i["subject_id"] == obs_id)
    r = client.post(f"{PREFIX}/review/{item['id']}/decision", json={"decision": "approve"}, headers=ADMIN)
    assert r.status_code == 200, r.text


def _setup_cross_venue(client):
    a = _monitored(client, "Providence Board", "https://prov.invalid")
    b = _monitored(client, "Newport Classifieds", "https://newport.invalid")
    # The same phone + @ravenxo handle co-occur in a lead at BOTH venues.
    oa = _lead(client, a, "Ad: call +1 401 555 0142, ask for @ravenxo")
    ob = _lead(client, b, "Different board, same +1 401 555 0142 — @ravenxo")
    return oa, ob


# --- requires approved evidence -------------------------------------------------


def test_no_links_proposed_from_unapproved_leads(client):
    _setup_cross_venue(client)  # leads proposed, not yet approved
    res = client.post(PROPOSE, headers=ANA).json()
    assert res["proposed"] == 0  # relationships may only cite approved observations


def test_cross_venue_link_proposed_after_approval(client):
    oa, ob = _setup_cross_venue(client)
    _approve(client, oa)
    _approve(client, ob)

    res = client.post(PROPOSE, headers=ANA)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["proposed"] == 1
    link = body["links"][0]
    assert link["relationship_type"] == "appears_with"
    assert link["venue_count"] == 2
    assert {link["source_value"], link["target_value"]} == {"+14015550142", "ravenxo"}

    # The proposed relationship is in the review queue (system_proposed, awaiting an analyst).
    rels = client.get(f"{PREFIX}/relationships?status=proposed", headers=ADMIN).json()
    assert any(r["id"] == link["relationship_id"] for r in rels)
    queue = client.get(f"{PREFIX}/review?status=proposed", headers=ADMIN).json()
    assert any(i["subject_id"] == link["relationship_id"] for i in queue)


def test_links_are_not_re_proposed(client):
    oa, ob = _setup_cross_venue(client)
    _approve(client, oa)
    _approve(client, ob)
    first = client.post(PROPOSE, headers=ANA).json()
    assert first["proposed"] == 1
    second = client.post(PROPOSE, headers=ANA).json()
    assert second["proposed"] == 0  # already linked → not re-proposed


def test_single_venue_cooccurrence_is_not_proposed(client):
    a = _monitored(client, "Solo Board", "https://solo.invalid")
    o = _lead(client, a, "call +1 401 555 0142, @ravenxo")  # both identifiers, one venue
    _approve(client, o)
    res = client.post(PROPOSE, headers=ANA).json()
    assert res["proposed"] == 0  # co-occurrence within a single venue is not a cross-venue link


def test_propose_links_requires_create_capability(client):
    assert client.post(PROPOSE, headers={"X-ORCA-User": "vic"}).status_code == 403


def test_propose_links_is_audited(client):
    oa, ob = _setup_cross_venue(client)
    _approve(client, oa)
    _approve(client, ob)
    client.post(PROPOSE, headers=ANA)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.links", headers=ADMIN).json()
    assert any(e["action"] == "hunting.links.proposed" for e in entries)
