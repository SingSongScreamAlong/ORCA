"""Hunting Grounds — operator-managed AOR watchlist.

Operators manage the AORs the autonomous cadence sweeps from the UI (admin-gated), without a
redeploy. The persisted watchlist takes precedence over the env fallback. These tests cover the
CRUD surface, dedup, RBAC, audit, and that a sweep with no explicit AORs uses the watchlist.
"""

from __future__ import annotations

PREFIX = "/api/v1"
WL = f"{PREFIX}/hunting/watchlist"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}


def test_watchlist_empty_by_default(client):
    assert client.get(WL, headers=ANA).json() == []


def test_add_and_list_and_remove(client):
    a = client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)
    assert a.status_code == 201, a.text
    assert a.json()["aor"] == "Rhode Island"
    assert a.json()["added_by"] == "admin"
    client.post(WL, json={"aor": "Connecticut"}, headers=ADMIN)

    aors = [e["aor"] for e in client.get(WL, headers=ANA).json()]
    assert aors == ["Connecticut", "Rhode Island"]  # sorted

    assert client.delete(f"{WL}/Connecticut", headers=ADMIN).status_code == 204
    assert [e["aor"] for e in client.get(WL, headers=ANA).json()] == ["Rhode Island"]


def test_add_dedups_case_insensitively(client):
    client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)
    client.post(WL, json={"aor": "rhode island"}, headers=ADMIN)
    assert len(client.get(WL, headers=ANA).json()) == 1


def test_watchlist_mutations_are_admin_only(client):
    assert client.post(WL, json={"aor": "Maine"}, headers=ANA).status_code == 403
    client.post(WL, json={"aor": "Maine"}, headers=ADMIN)
    assert client.delete(f"{WL}/Maine", headers=ANA).status_code == 403


def test_watchlist_changes_are_audited(client):
    client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)
    client.delete(f"{WL}/Rhode Island", headers=ADMIN)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.watchlist", headers=ADMIN).json()
    actions = [e["action"] for e in entries]
    assert "hunting.watchlist.added" in actions
    assert "hunting.watchlist.removed" in actions


# --- the watchlist drives the sweep ---------------------------------------------


def test_status_reflects_persisted_watchlist(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_AORS", raising=False)
    client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)
    body = client.get(f"{PREFIX}/hunting/discovery/status", headers=ANA).json()
    assert body["aors"] == ["Rhode Island"]


def test_sweep_uses_watchlist_when_no_explicit_aors(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_AORS", raising=False)  # no env fallback
    client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)
    client.post(WL, json={"aor": "Connecticut"}, headers=ADMIN)

    body = client.post(f"{PREFIX}/hunting/discovery/sweep?limit=1", headers=ANA).json()
    assert {r["aor"] for r in body["results"]} == {"Rhode Island", "Connecticut"}


def test_persisted_watchlist_overrides_env(client, monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_AORS", "Maine")  # env fallback present
    client.post(WL, json={"aor": "Rhode Island"}, headers=ADMIN)  # persisted wins
    body = client.post(f"{PREFIX}/hunting/discovery/sweep?limit=1", headers=ANA).json()
    assert [r["aor"] for r in body["results"]] == ["Rhode Island"]
