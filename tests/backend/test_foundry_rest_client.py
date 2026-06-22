"""REST Foundry connector (v1.2).

Exercises the real httpx-based read-only connector against an **injected mock transport**
(no network, no tenant): the OAuth2 client-credentials exchange, bearer auth on reads, the
v2 ontology endpoints, deterministic parsing, and — critically — that secrets never appear
in error messages. No test contacts a live Foundry tenant.
"""

from __future__ import annotations

import httpx
import pytest

from app.foundry.client import build_foundry_client
from app.foundry.config import FoundryConfig
from app.foundry.errors import FoundryConnectionError
from app.foundry.rest_client import RestFoundryClient

SECRET_CS = "SUPER-SECRET-CLIENT-SECRET"
PRE_TOKEN = "PRE-ISSUED-TOKEN-VALUE"


def _cfg(**over) -> FoundryConfig:
    base = dict(
        enabled=True,
        tenant_url="https://demo-tenant.example.invalid",
        ontology_api_name="orca-demo",
        client_id="client-abc",
        client_secret=SECRET_CS,
        test_object_type="OrcaCase",
    )
    base.update(over)
    return FoundryConfig(**base)


def _client(config, record, *, token_status=200, get_status=200) -> RestFoundryClient:
    def handler(request: httpx.Request) -> httpx.Response:
        record.append(
            {
                "method": request.method,
                "path": request.url.path,
                "auth": request.headers.get("Authorization"),
                "params": dict(request.url.params),
            }
        )
        path = request.url.path
        if path.endswith("/multipass/api/oauth2/token"):
            if token_status >= 400:
                return httpx.Response(token_status, json={"error": "invalid_client"})
            return httpx.Response(200, json={"access_token": "tok-XYZ", "expires_in": 3600})
        if get_status >= 400:
            return httpx.Response(get_status, json={"error": "forbidden"})
        if "/objectTypes/" in path:
            return httpx.Response(200, json={"apiName": "OrcaCase", "primaryKey": "caseId"})
        if "/objects/" in path:
            if request.url.params.get("pageSize"):
                return httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})
            return httpx.Response(200, json={"id": path.rsplit("/", 1)[-1], "properties": {}})
        if path.endswith("/api/v2/ontologies"):
            return httpx.Response(200, json={"data": [{"apiName": "orca-demo"}]})
        return httpx.Response(404, json={"error": "not found"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return RestFoundryClient(config, http_client=http)


# --- auth -----------------------------------------------------------------------


def test_client_credentials_exchange_then_bearer_get():
    record: list[dict] = []
    client = _client(_cfg(), record)
    result = client.health_check()
    assert result["mode"] == "real" and result["reachable"] is True
    assert result["ontology_count"] == 1
    # A token exchange happened, then the read carried the issued bearer token.
    assert any(r["path"].endswith("/oauth2/token") and r["method"] == "POST" for r in record)
    get = next(r for r in record if r["path"].endswith("/api/v2/ontologies"))
    assert get["auth"] == "Bearer tok-XYZ"


def test_pre_issued_token_skips_exchange():
    record: list[dict] = []
    client = _client(_cfg(token=PRE_TOKEN, client_id=None, client_secret=None), record)
    client.health_check()
    assert not any(r["path"].endswith("/oauth2/token") for r in record)  # no exchange
    get = next(r for r in record if r["path"].endswith("/api/v2/ontologies"))
    assert get["auth"] == f"Bearer {PRE_TOKEN}"


# --- read-only endpoints --------------------------------------------------------


def test_object_type_metadata_path():
    record: list[dict] = []
    meta = _client(_cfg(), record).get_object_type_metadata("OrcaCase")
    assert meta["apiName"] == "OrcaCase"
    assert any(r["path"] == "/api/v2/ontologies/orca-demo/objectTypes/OrcaCase" for r in record)


def test_object_by_id_path():
    record: list[dict] = []
    obj = _client(_cfg(), record).get_object_by_id("OrcaCase", "demo-001")
    assert obj["id"] == "demo-001"
    assert any(r["path"] == "/api/v2/ontologies/orca-demo/objects/OrcaCase/demo-001" for r in record)


def test_list_demo_objects_uses_page_size():
    record: list[dict] = []
    objs = _client(_cfg(), record).list_demo_objects("OrcaCase", limit=2)
    assert len(objs) == 2
    listing = next(r for r in record if r["path"].endswith("/objects/OrcaCase"))
    assert listing["params"].get("pageSize") == "2"


# --- failures are safe (no secrets) ---------------------------------------------


def test_read_http_error_is_safe():
    record: list[dict] = []
    client = _client(_cfg(), record, get_status=403)
    with pytest.raises(FoundryConnectionError) as exc:
        client.health_check()
    msg = str(exc.value)
    assert "403" in msg
    assert SECRET_CS not in msg


def test_token_rejection_is_safe():
    record: list[dict] = []
    client = _client(_cfg(), record, token_status=401)
    with pytest.raises(FoundryConnectionError) as exc:
        client.health_check()
    msg = str(exc.value)
    assert "401" in msg
    assert SECRET_CS not in msg  # never echo the secret-bearing token request


def test_secret_never_appears_in_any_error():
    for kw in ({"get_status": 500}, {"token_status": 400}):
        record: list[dict] = []
        client = _client(_cfg(token=PRE_TOKEN), record, **kw)
        try:
            client.health_check()
        except FoundryConnectionError as exc:
            assert SECRET_CS not in str(exc)
            assert PRE_TOKEN not in str(exc)


# --- factory --------------------------------------------------------------------


def test_build_client_returns_rest_when_enabled():
    client = build_foundry_client(_cfg())  # constructs httpx.Client lazily; no network yet
    assert isinstance(client, RestFoundryClient)
    assert client.mode == "real"


def test_build_client_returns_sdk_placeholder_when_selected():
    from app.foundry.real_client import RealFoundryClient

    client = build_foundry_client(_cfg(client_kind="sdk"))
    assert isinstance(client, RealFoundryClient)
