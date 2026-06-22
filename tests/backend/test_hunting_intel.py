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
