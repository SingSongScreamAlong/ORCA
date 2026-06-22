"""Hunting Grounds — automated collection.

Collection pulls **text-only** candidate leads from *monitored* sources and proposes each as an
observation in the review queue (analysts decide). These tests prove the boundary in code:

* it is **disabled by default** (clear 400 until configured);
* it runs **only against monitored sources** (422 otherwise);
* it **only proposes** — leads enter the review queue as proposed observations;
* it is **CSAM-safe**: the lead type has no media field, and the http provider reads only text;
* the real ``http`` provider talks only to a configured endpoint (injected mock transport — no
  network) and **never leaks the API key**;
* every run is written to the central **audit** log.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.schemas.hunting import HuntingLeadCreate
from app.services.hunting_collection import (
    CollectionConfigError,
    CollectionConnectionError,
    CollectionNotEnabled,
    HttpCollectionProvider,
    HuntingCollectionConfig,
    MockCollectionProvider,
    build_collection_provider,
)

PREFIX = "/api/v1"
SRC = f"{PREFIX}/hunting/sources"
COLLECT_ALL = f"{PREFIX}/hunting/collection/run"
STATUS = f"{PREFIX}/hunting/collection/status"
ADMIN = {"X-ORCA-User": "admin"}
ANA = {"X-ORCA-User": "ana"}

API_KEY = "SUPER-SECRET-COLLECTION-KEY"

AUTH = {
    "lawful_basis": "publicly available; licensed feed #RI-2026-04",
    "access_method": "licensed search API (read-only)",
    "jurisdiction": "Rhode Island, USA",
}


def _monitored(client, name="M", url="https://m.invalid"):
    sid = client.post(
        SRC,
        json={"name": name, "url": url, "category": "escort_listing", "aor": "Rhode Island"},
        headers=ANA,
    ).json()["id"]
    client.post(f"{SRC}/{sid}/authorize", json=AUTH, headers=ADMIN)
    client.post(f"{SRC}/{sid}/monitor", headers=ADMIN)
    return sid


def _enable_mock(monkeypatch):
    monkeypatch.setenv("ORCA_HUNTING_COLLECTION_PROVIDER", "mock")


# --- CSAM-safety is structural --------------------------------------------------


def test_collected_lead_type_has_no_media_field():
    # The whole pipeline is CSAM-safe because a lead simply cannot carry media.
    fields = set(HuntingLeadCreate.model_fields)
    assert not (fields & {"image", "media", "media_url", "attachment", "photo", "video"})
    assert "summary" in fields  # text only


# --- disabled by default --------------------------------------------------------


def test_collection_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_COLLECTION_PROVIDER", raising=False)
    sid = _monitored(client)
    resp = client.post(f"{SRC}/{sid}/collect", headers=ANA)
    assert resp.status_code == 400
    assert "disabled" in resp.json()["detail"].lower()


def test_status_reports_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_COLLECTION_PROVIDER", raising=False)
    body = client.get(STATUS, headers=ANA).json()
    assert body["provider"] == "disabled"
    assert body["enabled"] is False


# --- per-source collection (mock) -----------------------------------------------


def test_collect_from_monitored_source_proposes_observations(client, monkeypatch):
    _enable_mock(monkeypatch)
    sid = _monitored(client)
    resp = client.post(f"{SRC}/{sid}/collect?limit=2", headers=ANA)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert len(body["proposed_observation_ids"]) == 2

    # The leads are now proposed observations in the review queue.
    queue = client.get(f"{PREFIX}/review?status=proposed", headers=ADMIN).json()
    subjects = {r["subject_id"] for r in queue}
    assert all(oid in subjects for oid in body["proposed_observation_ids"])
    # The synthetic phone hint was resolved into an entity.
    entities = client.get(f"{PREFIX}/entities", headers=ADMIN).json()
    assert any(e["value"].startswith("+1555010") for e in entities)


def test_collect_requires_monitored_source(client, monkeypatch):
    _enable_mock(monkeypatch)
    # proposed (not monitored) → 422
    sid = client.post(
        SRC,
        json={"name": "P", "url": "https://p.invalid", "category": "forum", "aor": "Maine"},
        headers=ANA,
    ).json()["id"]
    resp = client.post(f"{SRC}/{sid}/collect", headers=ANA)
    assert resp.status_code == 422
    assert "monitored" in resp.json()["detail"].lower()


def test_collect_requires_create_capability(client, monkeypatch):
    _enable_mock(monkeypatch)
    sid = _monitored(client)
    assert client.post(f"{SRC}/{sid}/collect", headers={"X-ORCA-User": "vic"}).status_code == 403


def test_collect_is_audited(client, monkeypatch):
    _enable_mock(monkeypatch)
    sid = _monitored(client)
    client.post(f"{SRC}/{sid}/collect?limit=1", headers=ANA)
    entries = client.get(f"{PREFIX}/audit?action_prefix=hunting.collection", headers=ADMIN).json()
    assert any(e["action"] == "hunting.collection.run" for e in entries)


# --- collect-all sweep ----------------------------------------------------------


def test_collection_run_sweeps_only_monitored_sources(client, monkeypatch):
    _enable_mock(monkeypatch)
    _monitored(client, name="A", url="https://a.invalid")
    _monitored(client, name="B", url="https://b.invalid")
    # A proposed (non-monitored) source is ignored by the sweep.
    client.post(
        SRC,
        json={"name": "C", "url": "https://c.invalid", "category": "forum", "aor": "Maine"},
        headers=ANA,
    )
    body = client.post(f"{COLLECT_ALL}?limit=2", headers=ANA).json()
    assert body["sources_collected"] == 2
    assert body["total_proposed"] == 4  # 2 monitored x 2 leads
    audit = client.get(f"{PREFIX}/audit?action_prefix=hunting.collection.sweep", headers=ADMIN).json()
    assert audit and audit[0]["context"]["sources_collected"] == 2


def test_collection_run_disabled_returns_400(client, monkeypatch):
    monkeypatch.delenv("ORCA_HUNTING_COLLECTION_PROVIDER", raising=False)
    _monitored(client)
    assert client.post(COLLECT_ALL, headers=ANA).status_code == 400


# --- mock provider unit ---------------------------------------------------------


def test_mock_provider_offline_and_text_only():
    src = SimpleNamespace(name="Site", url="https://m.invalid", aor="Rhode Island")
    leads = MockCollectionProvider().collect(src, limit=3)
    assert len(leads) == 3
    assert all(isinstance(lead, HuntingLeadCreate) for lead in leads)
    assert all(lead.summary for lead in leads)  # text present
    assert leads[0].entities[0].entity_type.value == "phone_number"


# --- config / secret safety -----------------------------------------------------


def test_config_redacts_api_key():
    cfg = HuntingCollectionConfig(provider="http", url="https://c.example.invalid", api_key=API_KEY)
    assert API_KEY not in repr(cfg)
    assert cfg.safe_dict()["api_key"] == "***redacted***"


def test_http_provider_requires_lawful_basis():
    cfg = HuntingCollectionConfig(provider="http", url="https://c.example.invalid")
    assert "ORCA_HUNTING_COLLECTION_LAWFUL_BASIS" in cfg.missing_fields()
    with pytest.raises(CollectionConfigError):
        build_collection_provider(cfg)


def test_build_disabled_raises_not_enabled():
    with pytest.raises(CollectionNotEnabled):
        build_collection_provider(HuntingCollectionConfig(provider="disabled"))


def test_tor_requires_darkweb_acknowledgment():
    cfg = HuntingCollectionConfig(
        provider="http", url="http://svc.onion/api", lawful_basis="x",
        tor_proxy="socks5://127.0.0.1:9050",
    )
    assert cfg.tor_enabled is True
    assert any("DARKWEB_ACK" in m for m in cfg.missing_fields())
    with pytest.raises(CollectionConfigError):
        build_collection_provider(cfg)
    # With the acknowledgment recorded, it builds.
    ok = HuntingCollectionConfig(
        provider="http", url="http://svc.onion/api", lawful_basis="x",
        tor_proxy="socks5://127.0.0.1:9050", darkweb_acknowledged=True,
    )
    assert ok.is_configured() is True
    assert build_collection_provider(ok).name == "http"


# --- http provider against an injected mock transport (no network) --------------


def _http_provider(handler, **cfg_over) -> HttpCollectionProvider:
    base = dict(
        provider="http",
        url="https://c.example.invalid/collect",
        api_key=API_KEY,
        lawful_basis="licensed OSINT data agreement #RI-2026-05",
        results_path="results",
    )
    base.update(cfg_over)
    cfg = HuntingCollectionConfig(**base)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpCollectionProvider(cfg, http_client=http)


def _source():
    return SimpleNamespace(name="Site", url="https://m.invalid/listing", aor="Rhode Island")


def test_http_provider_parses_text_leads_and_sends_bearer():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "summary": "Ad reuses phone +15550100000",
                        "entities": [{"entity_type": "phone_number", "value": "+15550100000"}],
                    },
                    {"summary": "Second ad, no entities"},
                    {"no_summary": "skipped"},
                ]
            },
        )

    leads = _http_provider(handler).collect(_source(), limit=5)
    assert [lead.summary for lead in leads] == ["Ad reuses phone +15550100000", "Second ad, no entities"]
    assert leads[0].entities[0].value == "+15550100000"
    assert seen["auth"] == f"Bearer {API_KEY}"
    assert seen["params"]["source"] == "https://m.invalid/listing"


def test_http_provider_skips_unknown_entity_types():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"results": [{"summary": "x", "entities": [{"entity_type": "not_a_type", "value": "v"}]}]},
        )

    leads = _http_provider(handler).collect(_source(), limit=5)
    assert leads[0].entities == []  # malformed hint dropped, lead kept


def test_http_error_is_safe_no_secret():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    with pytest.raises(CollectionConnectionError) as exc:
        _http_provider(handler).collect(_source())
    assert "403" in str(exc.value)
    assert API_KEY not in str(exc.value)


def test_http_non_json_is_safe():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    with pytest.raises(CollectionConnectionError):
        _http_provider(handler).collect(_source())
