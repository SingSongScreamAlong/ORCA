"""Hunting Grounds — autonomous discovery engine.

The engine lets ORCA *seek* new venues so the operator need not trawl — but autonomy can
never outrun the law. These tests prove the boundary in code:

* it is **disabled by default** (clear 400 until configured);
* it can **only propose** — candidates enter as ``proposed`` discovery jobs, deduped by URL;
* the real ``http`` provider talks only to a **configured** endpoint (exercised via an injected
  mock transport — no network) and **never leaks the API key** in errors;
* the ``http`` provider refuses to build without a recorded **lawful basis**;
* every autonomous run is written to the central **audit** log.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.security import Principal
from app.models.user import Role
from app.services.hunting_discovery import (
    DiscoveryConfigError,
    DiscoveryConnectionError,
    DiscoveryNotEnabled,
    HttpDiscoveryProvider,
    HuntingDiscoveryConfig,
    HuntingDiscoveryService,
    MockDiscoveryProvider,
    build_discovery_provider,
)

PREFIX = "/api/v1"
AUTO = f"{PREFIX}/hunting/discovery/auto"
STATUS = f"{PREFIX}/hunting/discovery/status"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

API_KEY = "SUPER-SECRET-DISCOVERY-KEY"


def _enable_mock(monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_DISCOVERY_PROVIDER", "mock")


# --- disabled by default --------------------------------------------------------


def test_auto_discovery_disabled_by_default_returns_clear_400(client, monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_PROVIDER", raising=False)
    resp = client.post(f"{AUTO}?aor=Rhode%20Island", headers=ANA)
    assert resp.status_code == 400
    assert "disabled" in resp.json()["detail"].lower()


def test_status_reports_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_DISCOVERY_PROVIDER", raising=False)
    body = client.get(STATUS, headers=ANA).json()
    assert body["provider"] == "disabled"
    assert body["enabled"] is False
    assert body["configured"] is False


# --- mock provider through the endpoint -----------------------------------------


def test_auto_discovery_proposes_candidates_as_discovery_jobs(client, monkeypatch):
    _enable_mock(monkeypatch)
    resp = client.post(f"{AUTO}?aor=Rhode%20Island&limit=3", headers=ANA)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert len(body["proposed"]) == 3
    assert body["skipped_existing"] == 0
    assert all(s["status"] == "proposed" for s in body["proposed"])
    assert all(s["discovery_method"] == "discovery_job" for s in body["proposed"])
    assert all(s["aor"] == "Rhode Island" for s in body["proposed"])


def test_auto_discovery_dedups_by_url_on_rerun(client, monkeypatch):
    _enable_mock(monkeypatch)
    client.post(f"{AUTO}?aor=Rhode%20Island&limit=3", headers=ANA)
    second = client.post(f"{AUTO}?aor=Rhode%20Island&limit=3", headers=ANA).json()
    assert second["proposed"] == []
    assert second["skipped_existing"] == 3


def test_auto_discovery_requires_create_capability(client, monkeypatch):
    _enable_mock(monkeypatch)
    # 'vic' is a viewer — cannot create observations, so cannot trigger the hunt.
    assert client.post(f"{AUTO}?aor=Rhode%20Island", headers={"X-ORCA-User": "vic"}).status_code == 403


def test_auto_discovery_is_audited(client, monkeypatch):
    _enable_mock(monkeypatch)
    client.post(f"{AUTO}?aor=Rhode%20Island&limit=2", headers=ANA)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.discovery", headers=ADMIN).json()
    auto = [e for e in entries if e["action"] == "hunting.discovery.auto"]
    assert auto, "expected a hunting.discovery.auto audit entry"
    assert auto[0]["context"]["provider"] == "mock"
    assert auto[0]["context"]["proposed"] == 2
    assert auto[0]["case_id"] is None


# --- mock provider unit ---------------------------------------------------------


def test_mock_provider_is_deterministic_and_offline():
    out = MockDiscoveryProvider().discover("Rhode Island", limit=4)
    again = MockDiscoveryProvider().discover("Rhode Island", limit=4)
    assert len(out) == 4
    assert [c.url for c in out] == [c.url for c in again]  # deterministic
    assert all(c.url.endswith(".invalid") for c in out)  # synthetic, offline


# --- config / secret safety -----------------------------------------------------


def test_config_redacts_api_key():
    cfg = HuntingDiscoveryConfig(provider="http", url="https://src.example.invalid", api_key=API_KEY)
    assert API_KEY not in repr(cfg)
    assert cfg.safe_dict()["api_key"] == "***redacted***"


def test_http_provider_requires_lawful_basis():
    # URL present but no lawful basis recorded → refuses to build.
    cfg = HuntingDiscoveryConfig(provider="http", url="https://src.example.invalid")
    assert "ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS" in cfg.missing_fields()
    with pytest.raises(DiscoveryConfigError):
        build_discovery_provider(cfg)


def test_build_disabled_raises_not_enabled():
    with pytest.raises(DiscoveryNotEnabled):
        build_discovery_provider(HuntingDiscoveryConfig(provider="disabled"))


def test_build_unknown_provider_raises_config_error():
    with pytest.raises(DiscoveryConfigError):
        build_discovery_provider(HuntingDiscoveryConfig(provider="nope"))


# --- http provider against an injected mock transport (no network) --------------


def _http_provider(handler, **cfg_over) -> HttpDiscoveryProvider:
    base = dict(
        provider="http",
        url="https://src.example.invalid/discover",
        api_key=API_KEY,
        lawful_basis="licensed OSINT data agreement #RI-2026-02",
        results_path="results",
    )
    base.update(cfg_over)
    cfg = HuntingDiscoveryConfig(**base)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpDiscoveryProvider(cfg, http_client=http)


def test_http_provider_parses_candidates_and_sends_bearer():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"name": "RI Listings A", "url": "https://a.example.invalid"},
                    {"name": "RI Listings B", "url": "https://b.example.invalid"},
                    {"name": "No URL — skipped"},
                ]
            },
        )

    out = _http_provider(handler).discover("Rhode Island", limit=5)
    assert [c.url for c in out] == ["https://a.example.invalid", "https://b.example.invalid"]
    assert {c.name for c in out} == {"RI Listings A", "RI Listings B"}
    assert seen["auth"] == f"Bearer {API_KEY}"  # bearer auth carried
    assert seen["params"]["aor"] == "Rhode Island"


def test_http_provider_supports_nested_results_path():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"items": [{"name": "X", "url": "https://x.invalid"}]}})

    out = _http_provider(handler, results_path="data.items").discover("RI", limit=5)
    assert [c.url for c in out] == ["https://x.invalid"]


def test_http_error_is_safe_no_secret():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    with pytest.raises(DiscoveryConnectionError) as exc:
        _http_provider(handler).discover("RI")
    msg = str(exc.value)
    assert "403" in msg
    assert API_KEY not in msg


def test_http_network_error_is_safe_no_secret():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(DiscoveryConnectionError) as exc:
        _http_provider(handler).discover("RI")
    assert API_KEY not in str(exc.value)


def test_http_non_json_is_safe():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    with pytest.raises(DiscoveryConnectionError):
        _http_provider(handler).discover("RI")


# --- orchestration service with an injected provider ----------------------------


class _StubProvider:
    name = "stub"

    def __init__(self, candidates):
        self._candidates = candidates

    def discover(self, aor, *, limit=10):
        return self._candidates[:limit]


def test_service_with_injected_provider_proposes(client):
    # The service composes the registry's run_discovery; candidates become proposed sources.
    from app.repositories.uow import build_unit_of_work
    from app.schemas.hunting import HuntingDiscoveryCandidate

    principal = Principal(id="ana", username="ana", display_name="Ana", role=Role.ANALYST)
    cands = [HuntingDiscoveryCandidate(name="S", url="https://stub.invalid", notes="x")]
    uow = build_unit_of_work()
    result = HuntingDiscoveryService(uow, provider=_StubProvider(cands)).auto_discover("RI", principal)
    uow.commit()
    assert result.provider == "stub"
    assert len(result.proposed) == 1
    assert result.proposed[0].status.value == "proposed"


def test_service_handles_empty_discovery():
    principal = Principal(id="ana", username="ana", display_name="Ana", role=Role.ANALYST)
    result = HuntingDiscoveryService(None, provider=_StubProvider([])).auto_discover("RI", principal)
    assert result.proposed == []
    assert result.skipped_existing == 0
    assert result.provider == "stub"
