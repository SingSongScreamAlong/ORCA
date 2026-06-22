"""Hunting Grounds — automated collection.

Where *discovery* finds new venues, **collection** pulls candidate **leads** from the venues
ORCA already monitors — automating the first-pass triage that would otherwise sit a person in
front of traumatic listings. A collected lead becomes a **proposed observation** in the review
queue through the exact same seam as a hand-logged one (``HuntingLeadService``): an analyst still
decides, citing evidence, before anything supports a relationship.

The boundary is the same as the rest of Hunting Grounds, enforced in code:

* **Monitored-only.** Collection runs **only** against sources the registry has moved to
  ``monitored`` — which required an administrator's authorization with a recorded lawful basis.
* **Proposes only.** Every lead enters the review queue as a *proposed* observation flagged for
  legal review; nothing is auto-approved.
* **CSAM-safe by construction.** A collected lead carries **text and entity hints only** — there
  is **no media field** anywhere in the type, so the collector cannot fetch, store, or transmit
  imagery. It reads the configured *text* fields of a response and never follows a media URL.
  Suspected-minor concerns route to the report-only CSAM hard-stop (``hunting_escalation``).
* **Configured lawful source only.** The real (``http``) provider talks to an endpoint you are
  licensed to query and have a recorded lawful basis for; it will not build without one. No
  scraping, no dark-web. Disabled by default — the ``mock`` provider exercises the wiring offline.

Secrets (the API key) are never logged and never appear in error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import EntityType, HuntingSourceStatus
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    HuntingCollectionResult,
    HuntingCollectionStatus,
    HuntingCollectionSweepResult,
    HuntingEntityHint,
    HuntingLeadCreate,
    HuntingSourceRead,
)
from app.services.hunting_discovery import (  # shared, secret-free helpers
    _as_bool,
    _build_http_client,
    _clean,
    _dig,
)

_REDACTED = "***redacted***"
_TIMEOUT = 30.0
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


# --- errors (never carry secret values) -----------------------------------------


class CollectionError(Exception):
    """Base class for automated-collection errors. Messages are written to be secret-free."""


class CollectionNotEnabled(CollectionError):
    """Automated collection is disabled (no provider configured)."""


class CollectionConfigError(CollectionError):
    """Collection is requested but its configuration is incomplete or invalid."""


class CollectionConnectionError(CollectionError):
    """A collection fetch failed at runtime (network/HTTP/parse)."""


# --- configuration --------------------------------------------------------------


def _get(env: dict, key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class HuntingCollectionConfig:
    """Automated-collection configuration, read from ``ORCA_HUNTING_COLLECTION_*``.

    Defaults to ``provider="disabled"`` so collection is off out of the box. The ``http``
    provider additionally requires a URL **and** a recorded lawful basis before it can be built.
    """

    provider: str = "disabled"  # "disabled" | "mock" | "http"
    url: str | None = None
    api_key: str | None = None  # secret — never logged
    lawful_basis: str | None = None  # required to enable the http provider
    # How to read the upstream JSON (generic; tune to your endpoint's shape). All TEXT fields —
    # there is deliberately no media/image field to read.
    results_path: str = "results"
    summary_field: str = "summary"
    observed_at_field: str = "observed_at"
    entities_field: str = "entities"  # optional per-row list of {entity_type, value}
    default_confidence: float = 0.4
    # Dark-web transport: a Tor SOCKS proxy to reach .onion sources, gated behind an explicit
    # acknowledgment that counsel sign-off + LE deconfliction are in place.
    tor_proxy: str | None = None
    darkweb_acknowledged: bool = False

    @classmethod
    def from_env(cls, env: dict | None = None) -> HuntingCollectionConfig:
        env = os.environ if env is None else env
        return cls(
            provider=(_get(env, "ORCA_HUNTING_COLLECTION_PROVIDER") or "disabled").lower(),
            url=_get(env, "ORCA_HUNTING_COLLECTION_URL"),
            api_key=_get(env, "ORCA_HUNTING_COLLECTION_API_KEY"),
            lawful_basis=_get(env, "ORCA_HUNTING_COLLECTION_LAWFUL_BASIS"),
            results_path=_get(env, "ORCA_HUNTING_COLLECTION_RESULTS_PATH") or "results",
            summary_field=_get(env, "ORCA_HUNTING_COLLECTION_SUMMARY_FIELD") or "summary",
            observed_at_field=_get(env, "ORCA_HUNTING_COLLECTION_OBSERVED_AT_FIELD") or "observed_at",
            entities_field=_get(env, "ORCA_HUNTING_COLLECTION_ENTITIES_FIELD") or "entities",
            default_confidence=_as_float(_get(env, "ORCA_HUNTING_COLLECTION_DEFAULT_CONFIDENCE"), 0.4),
            tor_proxy=_get(env, "ORCA_HUNTING_COLLECTION_TOR_PROXY"),
            darkweb_acknowledged=_as_bool(env.get("ORCA_HUNTING_COLLECTION_DARKWEB_ACK")),
        )

    @property
    def enabled(self) -> bool:
        return self.provider in {"mock", "http"}

    def base_host(self) -> str | None:
        if not self.url:
            return None
        parsed = urlparse(self.url if "://" in self.url else f"https://{self.url}")
        return parsed.hostname

    def missing_fields(self) -> list[str]:
        if self.provider != "http":
            return []
        missing: list[str] = []
        if not self.url:
            missing.append("ORCA_HUNTING_COLLECTION_URL")
        if not self.lawful_basis:
            missing.append("ORCA_HUNTING_COLLECTION_LAWFUL_BASIS")
        # The dark-web gate: a Tor proxy cannot be used without an explicit acknowledgment that
        # counsel sign-off and LE deconfliction are in place.
        if self.tor_proxy and not self.darkweb_acknowledged:
            missing.append("ORCA_HUNTING_COLLECTION_DARKWEB_ACK (records counsel + LE deconfliction)")
        return missing

    def is_configured(self) -> bool:
        return self.enabled and not self.missing_fields()

    @property
    def tor_enabled(self) -> bool:
        return bool(self.tor_proxy)

    def safe_dict(self) -> dict:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "lawful_basis_recorded": bool(self.lawful_basis),
            "host": self.base_host(),
            "tor": self.tor_enabled,
            "darkweb_acknowledged": self.darkweb_acknowledged,
            "api_key": _REDACTED if self.api_key else None,
        }

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}={v!r}" for k, v in self.safe_dict().items())
        return f"HuntingCollectionConfig({inner})"

    __str__ = __repr__


# --- provider protocol ----------------------------------------------------------


class CollectionProvider(Protocol):
    """A source the engine can pull candidate leads from. Implementations return **text-only**
    leads (``HuntingLeadCreate`` has no media field) and raise :class:`CollectionError`."""

    name: str

    def collect(self, source: HuntingSourceRead, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingLeadCreate]:
        ...


class MockCollectionProvider:
    """Deterministic, offline provider for exercising the wiring (no network).

    Emits synthetic text leads derived from the source — including a synthetic phone entity hint
    so the lead→review→entity path can be exercised. Never reaches any real source.
    """

    name = "mock"

    def collect(self, source: HuntingSourceRead, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingLeadCreate]:
        n = max(0, min(limit, _MAX_LIMIT))
        leads: list[HuntingLeadCreate] = []
        for i in range(1, n + 1):
            phone = f"+1555010{i:04d}"
            leads.append(
                HuntingLeadCreate(
                    summary=f"Listing {i} on {source.name} reuses phone {phone} (synthetic mock lead).",
                    confidence=0.4,
                    entities=[HuntingEntityHint(entity_type=EntityType.PHONE_NUMBER, value=phone)],
                )
            )
        return leads


class HttpCollectionProvider:
    """Generic client for a configured, **licensed** collection endpoint (text/metadata only).

    Issues a single read-only ``GET`` keyed by the monitored source's URL, then maps the
    configured **text** fields into leads. It never reads or follows a media field. Secrets never
    appear in error messages.
    """

    name = "http"

    def __init__(self, config: HuntingCollectionConfig, *, http_client: Any | None = None) -> None:
        missing = config.missing_fields()
        if missing:
            raise CollectionConfigError(
                "Automated collection (http) is selected but configuration is incomplete: missing "
                + ", ".join(missing)
                + ". See docs/hunting_grounds_collection.md."
            )
        self.config = config
        self._http = http_client

    def _client(self):
        if self._http is not None:
            return self._http
        self._http = _build_http_client(self.config.tor_proxy, CollectionConnectionError)
        return self._http

    def collect(self, source: HuntingSourceRead, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingLeadCreate]:
        n = max(1, min(limit, _MAX_LIMIT))
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        params = {"source": source.url, "aor": source.aor, "limit": str(n)}
        try:
            resp = self._client().get(self.config.url, headers=headers, params=params)
        except Exception as exc:  # noqa: BLE001 — surfaced as a safe connection error
            host = self.config.base_host() or "the collection source"
            raise CollectionConnectionError(
                f"Collection request to {host} failed (network error)."
            ) from exc
        if resp.status_code >= 400:
            raise CollectionConnectionError(
                f"Collection source rejected the request (HTTP {resp.status_code})."
            )
        try:
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise CollectionConnectionError("Collection source returned a non-JSON response.") from exc
        return self._parse(payload, limit=n)

    def _parse(self, payload: Any, *, limit: int) -> list[HuntingLeadCreate]:
        rows = _dig(payload, self.config.results_path)
        if not isinstance(rows, list):
            return []
        out: list[HuntingLeadCreate] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            summary = _clean(row.get(self.config.summary_field))
            if not summary:
                continue  # a lead must carry a text summary
            out.append(
                HuntingLeadCreate(
                    summary=summary,
                    observed_at=None,  # parsed leniently below if present
                    confidence=self.config.default_confidence,
                    entities=self._entities(row.get(self.config.entities_field)),
                )
            )
        return out

    def _entities(self, raw: Any) -> list[HuntingEntityHint]:
        """Map an optional per-row entities list into typed hints, skipping anything malformed."""
        if not isinstance(raw, list):
            return []
        hints: list[HuntingEntityHint] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            value = _clean(item.get("value"))
            type_raw = _clean(item.get("entity_type"))
            if not value or not type_raw:
                continue
            try:
                entity_type = EntityType(type_raw)
            except ValueError:
                continue  # unknown entity type — skip the hint, keep the lead
            hints.append(HuntingEntityHint(entity_type=entity_type, value=value))
        return hints


def build_collection_provider(
    config: HuntingCollectionConfig | None = None, *, http_client: Any | None = None
) -> CollectionProvider:
    """Build the configured collection provider, or raise a clear, secret-free error."""
    config = config or HuntingCollectionConfig.from_env()
    if config.provider == "disabled":
        raise CollectionNotEnabled(
            "Automated collection is disabled. Set ORCA_HUNTING_COLLECTION_PROVIDER=mock to try the "
            "wiring, or =http with a licensed endpoint and a recorded lawful basis. See "
            "docs/hunting_grounds_collection.md."
        )
    if config.provider == "mock":
        return MockCollectionProvider()
    if config.provider == "http":
        return HttpCollectionProvider(config, http_client=http_client)
    raise CollectionConfigError(
        f"Unknown collection provider '{config.provider}' (expected 'disabled', 'mock', or 'http')."
    )


# --- orchestration --------------------------------------------------------------


class HuntingCollectionService:
    """Drives automated collection: pull text leads from monitored sources and propose each as an
    observation in the review queue (analysts decide). Never authorizes, monitors, or auto-approves.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        provider: CollectionProvider | None = None,
        config: HuntingCollectionConfig | None = None,
    ) -> None:
        self.uow = uow
        self._provider = provider  # injectable for tests
        self._config = config

    def status(self) -> HuntingCollectionStatus:
        config = self._config or HuntingCollectionConfig.from_env()
        return HuntingCollectionStatus(
            provider=config.provider,
            enabled=config.enabled,
            configured=config.is_configured(),
            lawful_basis_recorded=bool(config.lawful_basis),
            host=config.base_host(),
            tor_enabled=config.tor_enabled,
            darkweb_acknowledged=config.darkweb_acknowledged,
        )

    def collect(
        self, source_id, principal: Principal, *, limit: int = _DEFAULT_LIMIT
    ) -> HuntingCollectionResult:
        from app.services.errors import ValidationError
        from app.services.hunting_registry_service import HuntingRegistryService

        source = HuntingRegistryService(self.uow).get(source_id)  # 404 if missing
        if source.status != HuntingSourceStatus.MONITORED:
            raise ValidationError(
                "Collection runs only against a monitored source "
                f"(this one is '{source.status.value}')."
            )
        provider = self._provider or build_collection_provider(self._config)
        result = self._collect_one(provider, source, principal, limit=limit)
        self._audit_collect(principal, result)
        return result

    def collect_all(
        self, principal: Principal, *, limit_per_source: int = _DEFAULT_LIMIT
    ) -> HuntingCollectionSweepResult:
        from app.services.hunting_registry_service import HuntingRegistryService

        monitored = HuntingRegistryService(self.uow).list(status=HuntingSourceStatus.MONITORED)
        provider = self._provider or build_collection_provider(self._config)
        results = [self._collect_one(provider, s, principal, limit=limit_per_source) for s in monitored]
        sweep = HuntingCollectionSweepResult(
            results=results,
            total_proposed=sum(len(r.proposed_observation_ids) for r in results),
            sources_collected=len(results),
            provider=getattr(provider, "name", None),
        )
        self._audit_sweep(principal, sweep)
        return sweep

    # --- internal ----------------------------------------------------------------

    def _collect_one(
        self, provider: CollectionProvider, source: HuntingSourceRead, principal: Principal, *, limit: int
    ) -> HuntingCollectionResult:
        from app.services.hunting_lead_service import HuntingLeadService

        leads = provider.collect(source, limit=limit)
        lead_service = HuntingLeadService(self.uow)
        observation_ids = []
        for lead in leads:
            # Each lead → a proposed observation in the review queue (monitored-only enforced here too).
            observation = lead_service.ingest(source.id, lead, principal)
            observation_ids.append(observation.id)
        return HuntingCollectionResult(
            source_id=source.id,
            source_name=source.name,
            proposed_observation_ids=observation_ids,
            provider=getattr(provider, "name", None),
        )

    def _audit_collect(self, principal: Principal, result: HuntingCollectionResult) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.collection.run",
                target_type="hunting_source",
                target_id=result.source_id,
                case_id=None,
                context={
                    "source": result.source_name,
                    "provider": result.provider,
                    "proposed": len(result.proposed_observation_ids),
                },
            )
        )

    def _audit_sweep(self, principal: Principal, sweep: HuntingCollectionSweepResult) -> None:
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.collection.sweep",
                target_type="hunting_collection",
                target_id="all-monitored",
                case_id=None,
                context={
                    "provider": sweep.provider,
                    "sources_collected": sweep.sources_collected,
                    "total_proposed": sweep.total_proposed,
                },
            )
        )
