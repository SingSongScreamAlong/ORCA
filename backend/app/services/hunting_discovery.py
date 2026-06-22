"""Hunting Grounds — autonomous discovery engine.

This is "the hunt" the charter describes: ORCA can **autonomously seek new venues** in an
area of responsibility so the operator need not trawl traumatic listings by hand. It is
deliberately built so autonomy can never outrun the law:

* **It only ever proposes.** Every candidate enters the registry as ``proposed`` via
  :class:`~app.services.hunting_registry_service.HuntingRegistryService`. A human
  administrator still authorizes each source — with a recorded lawful basis — before anything
  is ever monitored. Discovery has no path to ``authorized``/``monitored``.
* **It reaches out only through a configured, lawful source.** The real provider is a generic
  client for a *licensed* discovery/OSINT endpoint you configure and that you have a recorded
  lawful basis to use (``ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS`` is required to enable it). It
  does **not** scrape search engines or sites against their terms, and it does **not** crawl
  the dark web. Nothing turns on until you point it at a source you are licensed to query.
* **It is CSAM-safe by construction.** Candidates carry text/metadata only — a name, a URL, a
  category, a note. There is no media field anywhere in the pipeline, so imagery cannot be
  fetched, stored, or transmitted.
* **It is disabled by default.** With no configuration the engine is off; the ``mock`` provider
  exists only to exercise the wiring with synthetic ``.invalid`` candidates (no network).

Secrets (the API key) are never logged and never appear in error messages.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from app.core.audit import new_audit_entry
from app.core.security import Principal
from app.models.enums import HuntingSourceCategory
from app.repositories.uow import UnitOfWork
from app.schemas.hunting import (
    HuntingDiscoveryCandidate,
    HuntingDiscoveryResult,
    HuntingDiscoveryRun,
    HuntingDiscoveryStatus,
)

_REDACTED = "***redacted***"
_TIMEOUT = 30.0
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


# --- errors (never carry secret values) -----------------------------------------


class DiscoveryError(Exception):
    """Base class for autonomous-discovery errors. Messages are written to be secret-free."""


class DiscoveryNotEnabled(DiscoveryError):
    """Autonomous discovery is disabled (no provider configured)."""


class DiscoveryConfigError(DiscoveryError):
    """Discovery is requested but its configuration is incomplete or invalid."""


class DiscoveryConnectionError(DiscoveryError):
    """A discovery fetch failed at runtime (network/HTTP/parse)."""


# --- configuration --------------------------------------------------------------


def _get(env: dict, key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class HuntingDiscoveryConfig:
    """Autonomous-discovery configuration, read from ``ORCA_HUNTING_DISCOVERY_*``.

    Defaults to ``provider="disabled"`` so the engine is off in CI and out of the box. The
    ``http`` provider additionally requires a URL **and** a recorded lawful basis before it can
    be built — the legal gate is enforced here, not by convention.
    """

    provider: str = "disabled"  # "disabled" | "mock" | "http"
    url: str | None = None
    api_key: str | None = None  # secret — never logged
    lawful_basis: str | None = None  # required to enable the http provider
    # How to read the upstream JSON (generic; tune to your endpoint's shape):
    results_path: str = "results"  # dotted path to the results array, e.g. "data.items"
    name_field: str = "name"
    url_field: str = "url"
    category: str = HuntingSourceCategory.OTHER.value  # default category for candidates

    @classmethod
    def from_env(cls, env: dict | None = None) -> HuntingDiscoveryConfig:
        env = os.environ if env is None else env
        return cls(
            provider=(_get(env, "ORCA_HUNTING_DISCOVERY_PROVIDER") or "disabled").lower(),
            url=_get(env, "ORCA_HUNTING_DISCOVERY_URL"),
            api_key=_get(env, "ORCA_HUNTING_DISCOVERY_API_KEY"),
            lawful_basis=_get(env, "ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS"),
            results_path=_get(env, "ORCA_HUNTING_DISCOVERY_RESULTS_PATH") or "results",
            name_field=_get(env, "ORCA_HUNTING_DISCOVERY_NAME_FIELD") or "name",
            url_field=_get(env, "ORCA_HUNTING_DISCOVERY_URL_FIELD") or "url",
            category=(_get(env, "ORCA_HUNTING_DISCOVERY_CATEGORY") or HuntingSourceCategory.OTHER.value),
        )

    @property
    def enabled(self) -> bool:
        return self.provider in {"mock", "http"}

    def base_host(self) -> str | None:
        """Host only (no path/query/credentials) — safe to display/log."""
        if not self.url:
            return None
        parsed = urlparse(self.url if "://" in self.url else f"https://{self.url}")
        return parsed.hostname

    def candidate_category(self) -> HuntingSourceCategory:
        try:
            return HuntingSourceCategory(self.category)
        except ValueError:
            return HuntingSourceCategory.OTHER

    def missing_fields(self) -> list[str]:
        """Required fields absent for the selected provider (only meaningful for ``http``)."""
        if self.provider != "http":
            return []
        missing: list[str] = []
        if not self.url:
            missing.append("ORCA_HUNTING_DISCOVERY_URL")
        # The legal gate: the http provider cannot be built without a recorded lawful basis.
        if not self.lawful_basis:
            missing.append("ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS")
        return missing

    def is_configured(self) -> bool:
        return self.enabled and not self.missing_fields()

    def safe_dict(self) -> dict:
        """Secret-free snapshot for status endpoints and logs."""
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "lawful_basis_recorded": bool(self.lawful_basis),
            "host": self.base_host(),
            "category": self.candidate_category().value,
            "api_key": _REDACTED if self.api_key else None,
        }

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}={v!r}" for k, v in self.safe_dict().items())
        return f"HuntingDiscoveryConfig({inner})"

    __str__ = __repr__


# --- provider protocol ----------------------------------------------------------


class DiscoveryProvider(Protocol):
    """A source the engine can autonomously query for candidate venues.

    Implementations return *candidates only* (text/metadata) — no media — and must never
    raise raw upstream errors that could leak a secret; they raise :class:`DiscoveryError`.
    """

    name: str

    def discover(self, aor: str, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingDiscoveryCandidate]:
        ...


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "aor"


class MockDiscoveryProvider:
    """Deterministic, offline provider for exercising the wiring (no network).

    Emits synthetic ``.invalid`` candidates derived from the AOR. Useful in tests and demos;
    it never reaches any real source. Selected with ``ORCA_HUNTING_DISCOVERY_PROVIDER=mock``.
    """

    name = "mock"

    def __init__(self, category: HuntingSourceCategory = HuntingSourceCategory.ESCORT_LISTING) -> None:
        self._category = category

    def discover(self, aor: str, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingDiscoveryCandidate]:
        n = max(0, min(limit, _MAX_LIMIT))
        slug = _slug(aor)
        return [
            HuntingDiscoveryCandidate(
                name=f"{aor} listings index {i}",
                url=f"https://{slug}-listings-{i}.invalid",
                category=self._category,
                notes="Synthetic candidate from the mock discovery provider (no network).",
            )
            for i in range(1, n + 1)
        ]


class HttpDiscoveryProvider:
    """Generic client for a configured, **licensed** discovery/OSINT JSON endpoint.

    Issues a single read-only ``GET`` with the AOR as a query parameter and a Bearer API key,
    then maps the configured result fields into text-only candidates. It is intentionally
    generic — point it at an endpoint you are licensed to query (``ORCA_HUNTING_DISCOVERY_URL``)
    and tune the field/path names to its response shape. No scraping, no dark-web crawling.

    Secrets never appear in error messages; only safe summaries (HTTP status, host) are surfaced.
    """

    name = "http"

    def __init__(self, config: HuntingDiscoveryConfig, *, http_client: Any | None = None) -> None:
        missing = config.missing_fields()
        if missing:
            raise DiscoveryConfigError(
                "Autonomous discovery (http) is selected but configuration is incomplete: missing "
                + ", ".join(missing)
                + ". See docs/hunting_grounds_discovery.md."
            )
        self.config = config
        self._http = http_client  # injectable httpx.Client for tests

    def _client(self):
        if self._http is not None:
            return self._http
        import httpx

        self._http = httpx.Client(timeout=_TIMEOUT)
        return self._http

    def discover(self, aor: str, *, limit: int = _DEFAULT_LIMIT) -> list[HuntingDiscoveryCandidate]:
        n = max(1, min(limit, _MAX_LIMIT))
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        params = {"aor": aor, "limit": str(n)}
        try:
            resp = self._client().get(self.config.url, headers=headers, params=params)
        except Exception as exc:  # noqa: BLE001 — surfaced as a safe connection error
            host = self.config.base_host() or "the discovery source"
            raise DiscoveryConnectionError(
                f"Discovery request to {host} failed (network error)."
            ) from exc
        if resp.status_code >= 400:
            # Never echo the request (it carries the API key) — only a safe summary.
            raise DiscoveryConnectionError(
                f"Discovery source rejected the request (HTTP {resp.status_code})."
            )
        try:
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise DiscoveryConnectionError("Discovery source returned a non-JSON response.") from exc
        return self._parse(payload, limit=n)

    def _parse(self, payload: Any, *, limit: int) -> list[HuntingDiscoveryCandidate]:
        rows = _dig(payload, self.config.results_path)
        if not isinstance(rows, list):
            return []
        category = self.config.candidate_category()
        out: list[HuntingDiscoveryCandidate] = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            url = _clean(row.get(self.config.url_field))
            if not url:
                continue  # a candidate without a URL is not addressable — skip it
            name = _clean(row.get(self.config.name_field)) or url
            out.append(
                HuntingDiscoveryCandidate(
                    name=name,
                    url=url,
                    category=category,
                    notes="Autonomously discovered via the configured licensed source.",
                )
            )
        return out


def _dig(payload: Any, path: str) -> Any:
    """Follow a dotted ``path`` into nested dicts; return the value or ``None``."""
    node: Any = payload
    for part in path.split("."):
        if not part:
            continue
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return None
    return node


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def build_discovery_provider(
    config: HuntingDiscoveryConfig | None = None, *, http_client: Any | None = None
) -> DiscoveryProvider:
    """Build the configured discovery provider, or raise a clear, secret-free error.

    Raises :class:`DiscoveryNotEnabled` when discovery is off, and :class:`DiscoveryConfigError`
    for an unknown provider or incomplete ``http`` configuration.
    """
    config = config or HuntingDiscoveryConfig.from_env()
    if config.provider == "disabled":
        raise DiscoveryNotEnabled(
            "Autonomous discovery is disabled. Set ORCA_HUNTING_DISCOVERY_PROVIDER=mock to try the "
            "wiring, or =http with a licensed endpoint and a recorded lawful basis. See "
            "docs/hunting_grounds_discovery.md."
        )
    if config.provider == "mock":
        return MockDiscoveryProvider(category=config.candidate_category())
    if config.provider == "http":
        return HttpDiscoveryProvider(config, http_client=http_client)
    raise DiscoveryConfigError(
        f"Unknown discovery provider '{config.provider}' "
        "(expected 'disabled', 'mock', or 'http')."
    )


# --- orchestration --------------------------------------------------------------


class HuntingDiscoveryService:
    """Drives an autonomous discovery pass: query the configured provider, then feed every
    candidate through the registry's ``run_discovery`` so each enters as ``proposed`` (deduped
    by URL). Authorization stays a separate, human, admin-only step — this service never
    authorizes or monitors anything. The run itself is recorded in the central audit log.
    """

    def __init__(
        self,
        uow: UnitOfWork | None = None,
        *,
        provider: DiscoveryProvider | None = None,
        config: HuntingDiscoveryConfig | None = None,
    ) -> None:
        self.uow = uow
        self._provider = provider  # injectable for tests
        self._config = config

    def status(self) -> HuntingDiscoveryStatus:
        """Secret-free posture of the engine (provider, enabled, configured, host)."""
        config = self._config or HuntingDiscoveryConfig.from_env()
        return HuntingDiscoveryStatus(
            provider=config.provider,
            enabled=config.enabled,
            configured=config.is_configured(),
            lawful_basis_recorded=bool(config.lawful_basis),
            host=config.base_host(),
            category=config.candidate_category(),
        )

    def auto_discover(
        self, aor: str, principal: Principal, *, limit: int = _DEFAULT_LIMIT
    ) -> HuntingDiscoveryResult:
        # Lazy import keeps the engine module importable without the full service stack and
        # avoids any import cycle through the registry service.
        from app.services.hunting_registry_service import HuntingRegistryService

        provider = self._provider or build_discovery_provider(self._config)
        candidates = provider.discover(aor, limit=limit)
        provider_name = getattr(provider, "name", None)

        if not candidates:
            result = HuntingDiscoveryResult(
                aor=aor, proposed=[], skipped_existing=0, provider=provider_name
            )
        else:
            run = HuntingDiscoveryRun(aor=aor, candidates=candidates)
            base = HuntingRegistryService(self.uow).run_discovery(run, principal)
            result = base.model_copy(update={"provider": provider_name})

        self._audit(principal, aor, result)
        return result

    def _audit(self, principal: Principal, aor: str, result: HuntingDiscoveryResult) -> None:
        if self.uow is None:
            return
        self.uow.audit.record(
            new_audit_entry(
                actor_id=principal.id,
                action="hunting.discovery.auto",
                target_type="hunting_discovery",
                target_id=aor,
                case_id=None,
                context={
                    "aor": aor,
                    "provider": result.provider,
                    "proposed": len(result.proposed),
                    "skipped_existing": result.skipped_existing,
                },
            )
        )
