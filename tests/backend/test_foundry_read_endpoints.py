"""Admin-only, read-only Foundry data endpoints (v1.3).

These surface the connector's reads inside the app. With Foundry disabled (the default for
tests/CI), the deterministic mock client answers — so the endpoints are exercised with no
network and no tenant. Every endpoint is admin-only and returns a ``mode`` field.
"""

from __future__ import annotations

import pytest

PREFIX = "/api/v1"
NON_ADMINS = ("ana", "rae", "vic", "partner", "nomad")


def _get(client, path: str, user: str):
    return client.get(f"{PREFIX}{path}", headers={"X-ORCA-User": user})


# --- discover -------------------------------------------------------------------


def test_discover_admin_returns_mock_ontologies_and_types(client):
    resp = _get(client, "/integrations/foundry/discover", "admin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "mock"  # Foundry disabled in tests → mock client
    assert any(o["apiName"] == "mock-ontology" for o in body["ontologies"])
    assert {t["apiName"] for t in body["object_types"]} >= {"OrcaCase", "OrcaEntity"}


@pytest.mark.parametrize("user", NON_ADMINS)
def test_discover_is_admin_only(client, user):
    assert _get(client, "/integrations/foundry/discover", user).status_code == 403


# --- object-type metadata -------------------------------------------------------


def test_object_type_metadata_admin(client):
    resp = _get(client, "/integrations/foundry/object-types/OrcaCase", "admin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "mock" and body["object_type"] == "OrcaCase"
    assert body["metadata"]["apiName"] == "OrcaCase"


@pytest.mark.parametrize("user", NON_ADMINS)
def test_object_type_metadata_is_admin_only(client, user):
    assert _get(client, "/integrations/foundry/object-types/OrcaCase", user).status_code == 403


# --- object listing -------------------------------------------------------------


def test_objects_listing_respects_limit(client):
    resp = _get(client, "/integrations/foundry/objects/OrcaCase?limit=2", "admin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "mock" and body["object_type"] == "OrcaCase"
    assert body["count"] == len(body["objects"]) <= 2


def test_objects_listing_rejects_out_of_range_limit(client):
    # Query validation: limit must be 1..50.
    assert _get(client, "/integrations/foundry/objects/OrcaCase?limit=0", "admin").status_code == 422
    assert _get(client, "/integrations/foundry/objects/OrcaCase?limit=999", "admin").status_code == 422


@pytest.mark.parametrize("user", NON_ADMINS)
def test_objects_listing_is_admin_only(client, user):
    assert _get(client, "/integrations/foundry/objects/OrcaCase", user).status_code == 403


# --- single object --------------------------------------------------------------


def test_object_by_id_admin(client):
    resp = _get(client, "/integrations/foundry/objects/OrcaCase/demo-001", "admin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["object_id"] == "demo-001"
    assert body["object"]["id"] == "demo-001"


@pytest.mark.parametrize("user", NON_ADMINS)
def test_object_by_id_is_admin_only(client, user):
    assert _get(client, "/integrations/foundry/objects/OrcaCase/demo-001", user).status_code == 403
