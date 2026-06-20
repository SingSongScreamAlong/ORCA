"""Foundry connection spike (v1.1).

Proves the connection scaffolding is safe and credential-free:

* config defaults to disabled and does not break startup without credentials
* enabling without required config yields a clear validation error
* secrets are redacted from repr / safe output
* the mock client's read-only methods return deterministic synthetic data
* the health endpoint/CLI produces safe output (no secrets); it is admin-only
* the real client fails gracefully when its SDK is absent
* nothing requires a live Foundry tenant
"""

from __future__ import annotations

import json

import pytest

from app.foundry.client import build_foundry_client
from app.foundry.config import FoundryConfig
from app.foundry.errors import (
    FoundryConfigError,
    FoundryDependencyMissing,
    FoundryNotEnabled,
)
from app.foundry.health import foundry_health
from app.foundry.mock_client import MockFoundryClient
from app.foundry.real_client import RealFoundryClient

PREFIX = "/api/v1"

SECRET_TOKEN = "SUPER-SECRET-TOKEN-VALUE"
SECRET_CS = "SUPER-SECRET-CLIENT-SECRET"


def _configured(**over) -> FoundryConfig:
    base = dict(
        enabled=True,
        tenant_url="https://demo-tenant.example.invalid",
        ontology_api_name="orca-demo",
        token=SECRET_TOKEN,
        test_object_type="OrcaCase",
        test_object_id="demo-case-001",
    )
    base.update(over)
    return FoundryConfig(**base)


# --- config ---------------------------------------------------------------------


def test_config_defaults_to_disabled():
    cfg = FoundryConfig.from_env({})
    assert cfg.enabled is False
    assert cfg.is_configured() is False
    assert cfg.auth_method() == "none"


def test_from_env_reads_values():
    cfg = FoundryConfig.from_env({
        "ORCA_FOUNDRY_ENABLED": "true",
        "ORCA_FOUNDRY_TENANT_URL": "https://t.example.invalid/x",
        "ORCA_FOUNDRY_TOKEN": SECRET_TOKEN,
        "ORCA_FOUNDRY_ONTOLOGY_API_NAME": "orca",
    })
    assert cfg.enabled is True
    assert cfg.auth_method() == "token"
    assert cfg.safe_host() == "t.example.invalid"
    assert cfg.is_configured() is True


def test_enabling_without_config_reports_missing_fields():
    cfg = FoundryConfig(enabled=True)
    missing = cfg.missing_fields()
    assert "ORCA_FOUNDRY_TENANT_URL" in missing
    assert "ORCA_FOUNDRY_ONTOLOGY_API_NAME" in missing
    assert any("TOKEN" in m for m in missing)
    health = foundry_health(cfg)
    assert health["ok"] is False
    assert health["errors"]


def test_secrets_are_redacted():
    cfg = _configured(client_id="client-123", client_secret=SECRET_CS)
    text = repr(cfg) + " " + str(cfg) + " " + json.dumps(cfg.safe_dict())
    assert SECRET_TOKEN not in text
    assert SECRET_CS not in text
    assert cfg.safe_dict()["token"] == "***redacted***"
    assert cfg.safe_dict()["client_secret"] == "***redacted***"


# --- mock client ----------------------------------------------------------------


def test_mock_health_check():
    result = MockFoundryClient().health_check()
    assert result["mode"] == "mock"
    assert result["reachable"] is True


def test_mock_object_type_metadata():
    meta = MockFoundryClient().get_object_type_metadata("OrcaCase")
    assert meta["apiName"] == "OrcaCase"
    assert meta["primaryKey"] == "caseId"
    assert any(p["apiName"] == "caseId" for p in meta["properties"])
    assert meta["synthetic"] is True


def test_mock_object_read_and_list():
    obj = MockFoundryClient().get_object_by_id("OrcaCase", "demo-case-001")
    assert obj["id"] == "demo-case-001"
    assert obj["synthetic"] is True
    objs = MockFoundryClient().list_demo_objects("OrcaCase", limit=2)
    assert 1 <= len(objs) <= 2
    assert all(o["synthetic"] for o in objs)


def test_mock_failure_mode():
    from app.foundry.errors import FoundryConnectionError

    with pytest.raises(FoundryConnectionError):
        MockFoundryClient(fail=True).health_check()


def test_disabled_config_builds_mock_client():
    client = build_foundry_client(FoundryConfig())  # disabled → mock fallback
    assert client.mode == "mock"


# --- health (library) -----------------------------------------------------------


def test_health_with_mock_client_emits_no_secrets():
    cfg = _configured(client_id="client-123", client_secret=SECRET_CS)
    health = foundry_health(cfg, client=MockFoundryClient())
    assert health["ok"] is True
    assert health["mode"] == "mock"
    blob = json.dumps(health)
    assert SECRET_TOKEN not in blob
    assert SECRET_CS not in blob


def test_disabled_health_is_safe():
    health = foundry_health(FoundryConfig())
    assert health["enabled"] is False
    assert health["mode"] == "disabled"
    assert health["ok"] is None


# --- real client (graceful, no SDK) ---------------------------------------------


def test_real_client_requires_enabled_and_config():
    with pytest.raises(FoundryNotEnabled):
        RealFoundryClient(FoundryConfig(enabled=False))
    with pytest.raises(FoundryConfigError):
        RealFoundryClient(FoundryConfig(enabled=True))  # enabled but unconfigured


def test_real_client_fails_gracefully_without_sdk(monkeypatch):
    monkeypatch.setenv("ORCA_FOUNDRY_SDK_MODULE", "orca_absent_sdk_xyz")
    cfg = _configured()
    client = RealFoundryClient(cfg)  # construction is fine; the call is what probes the SDK
    with pytest.raises(FoundryDependencyMissing) as exc:
        client.health_check()
    msg = str(exc.value)
    assert "not installed" in msg
    assert "foundry_connection_setup" in msg
    assert SECRET_TOKEN not in msg  # never leak secrets in errors


def test_enabled_health_without_sdk_is_safe(monkeypatch):
    monkeypatch.setenv("ORCA_FOUNDRY_SDK_MODULE", "orca_absent_sdk_xyz")
    health = foundry_health(_configured())
    assert health["ok"] is False
    assert health["mode"] == "real"
    assert SECRET_TOKEN not in json.dumps(health)


# --- endpoint -------------------------------------------------------------------


def test_health_endpoint_is_admin_only_and_safe(client):
    ok = client.get(f"{PREFIX}/integrations/foundry/health", headers={"X-ORCA-User": "admin"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["enabled"] is False
    assert SECRET_TOKEN not in ok.text
    # Non-admins cannot reach the diagnostic.
    for user in ("ana", "vic", "partner"):
        denied = client.get(f"{PREFIX}/integrations/foundry/health", headers={"X-ORCA-User": user})
        assert denied.status_code == 403, user
