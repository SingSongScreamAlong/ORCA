"""Foundry → ORCA entity import (v1.4).

With Foundry disabled (the test/CI default), the deterministic mock client supplies the
objects, so the import is exercised with no network. The import writes only ORCA entities
(deduped, idempotent) and is admin-only.
"""

from __future__ import annotations

import pytest

PREFIX = "/api/v1"
NON_ADMINS = ("ana", "rae", "vic", "partner", "nomad")

# The mock client's list_demo_objects returns objects with a top-level "id" like
# "demo-case-001"; we map that into ORCA entities.
IMPORT = {"object_type": "OrcaCase", "entity_type": "username", "value_property": "id", "limit": 3}


def _import(client, user="admin", **overrides):
    body = {**IMPORT, **overrides}
    return client.post(f"{PREFIX}/integrations/foundry/import", json=body, headers={"X-ORCA-User": user})


def test_import_creates_entities_from_mock(client):
    resp = _import(client)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mode"] == "mock"
    assert body["read"] == 3
    assert body["created"] == 3
    assert body["resolved_existing"] == 0
    assert len(body["entities"]) == 3
    assert all(e["entity_type"] == "username" for e in body["entities"])
    # The imported entities are now in ORCA's entity store.
    listed = client.get(f"{PREFIX}/entities", headers={"X-ORCA-User": "admin"}).json()
    values = {e["value"] for e in listed}
    assert {"demo-case-001", "demo-case-002", "demo-case-003"} <= values


def test_import_is_idempotent(client):
    first = _import(client).json()
    assert first["created"] == 3
    second = _import(client).json()
    # Same objects → deduped, nothing new created.
    assert second["created"] == 0
    assert second["resolved_existing"] == 3
    assert len(second["entities"]) == 3


def test_import_skips_objects_without_the_value_property(client):
    resp = _import(client, value_property="does_not_exist")
    body = resp.json()
    assert resp.status_code == 200
    assert body["read"] == 3
    assert body["created"] == 0
    assert body["skipped"] == 3
    assert body["entities"] == []


def test_import_rejects_invalid_entity_type(client):
    # entity_type must be a valid ORCA EntityType enum value.
    resp = _import(client, entity_type="aircraft")
    assert resp.status_code == 422


def test_import_rejects_out_of_range_limit(client):
    assert _import(client, limit=0).status_code == 422
    assert _import(client, limit=999).status_code == 422


@pytest.mark.parametrize("user", NON_ADMINS)
def test_import_is_admin_only(client, user):
    assert _import(client, user=user).status_code == 403


def test_import_does_not_persist_for_non_admin(client):
    # A denied import must not have written anything.
    _import(client, user="ana")
    listed = client.get(f"{PREFIX}/entities", headers={"X-ORCA-User": "admin"}).json()
    assert all(not e["value"].startswith("demo-case-") for e in listed)
