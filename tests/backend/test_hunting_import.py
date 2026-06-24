"""Hunting Grounds — bulk site import (bring-your-own hunting list).

The operator hands ORCA a list of sites to monitor, with the lawful basis they're watched under;
each is proposed (deduped by URL), authorized with that shared record, and set monitored in one
admin pass. Respects the authorization-first gate (a lawful basis is mandatory) and is admin-only.
"""

from __future__ import annotations

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
IMPORT = f"{SRC}/import"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

AUTH = {
    "lawful_basis": "publicly available; licensed feed",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _payload(sites, monitor=True, aor="Rhode Island", category="escort_listing"):
    return {"aor": aor, "category": category, "sites": sites, "authorization": AUTH, "monitor": monitor}


def test_import_proposes_authorizes_and_monitors(client):
    body = _payload(
        [
            {"url": "https://a.invalid/listings"},
            {"name": "Site B", "url": "https://b.invalid"},
        ]
    )
    res = client.post(IMPORT, json=body, headers=ADMIN)
    assert res.status_code == 201, res.text
    out = res.json()
    assert out["imported"] == 2 and out["monitored"] == 2 and out["skipped_existing"] == 0

    # Both are now monitored, carry the shared lawful basis, and a missing name defaults to the host.
    monitored = client.get(f"{SRC}?status=monitored", headers=ANA).json()
    by_url = {s["url"]: s for s in monitored}
    assert by_url["https://a.invalid/listings"]["name"] == "a.invalid"
    assert by_url["https://b.invalid"]["name"] == "Site B"
    assert all(s["lawful_basis"] == AUTH["lawful_basis"] for s in monitored)
    assert all(s["aor"] == "Rhode Island" for s in monitored)


def test_import_dedups_by_normalized_url(client):
    client.post(IMPORT, json=_payload([{"url": "https://dup.invalid"}]), headers=ADMIN)
    # Trailing slash / www / host-case variant is the same site — skipped, not re-created.
    res = client.post(IMPORT, json=_payload([{"url": "https://WWW.dup.invalid/"}]), headers=ADMIN).json()
    assert res["imported"] == 0 and res["skipped_existing"] == 1
    assert len(client.get(f"{SRC}?status=monitored", headers=ANA).json()) == 1


def test_import_without_monitor_stops_at_authorized(client):
    res = client.post(IMPORT, json=_payload([{"url": "https://hold.invalid"}], monitor=False), headers=ADMIN)
    out = res.json()
    assert out["imported"] == 1 and out["monitored"] == 0
    assert client.get(f"{SRC}?status=authorized", headers=ANA).json()[0]["url"] == "https://hold.invalid"
    assert client.get(f"{SRC}?status=monitored", headers=ANA).json() == []


def test_import_requires_a_lawful_basis(client):
    # The authorization record is mandatory — an empty lawful_basis is rejected by the schema (422).
    bad = _payload([{"url": "https://x.invalid"}])
    bad["authorization"] = {"lawful_basis": "", "access_method": "x", "jurisdiction": "y"}
    assert client.post(IMPORT, json=bad, headers=ADMIN).status_code == 422


def test_import_is_admin_only(client):
    assert client.post(IMPORT, json=_payload([{"url": "https://x.invalid"}]), headers=ANA).status_code == 403


def test_import_is_audited(client):
    client.post(IMPORT, json=_payload([{"url": "https://x.invalid"}]), headers=ADMIN)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.sources.imported", headers=ADMIN).json()
    assert any(e["action"] == "hunting.sources.imported" for e in entries)
