"""Foundry connection configuration (v1.1).

Reads ``ORCA_FOUNDRY_*`` environment variables, **defaults to disabled**, and is safe in
CI with no credentials. Secrets (`client_secret`, `token`) are never logged: ``repr`` and
``safe_dict`` redact them. Required fields are validated **only when enabled**.

Auth methods supported by this spike (pick one):
* ``token`` — a pre-issued bearer token (`ORCA_FOUNDRY_TOKEN`).
* ``client_credentials`` — OAuth2 client id + secret
  (`ORCA_FOUNDRY_CLIENT_ID` + `ORCA_FOUNDRY_CLIENT_SECRET`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_REDACTED = "***redacted***"


def _get(env: dict, key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class FoundryConfig:
    enabled: bool = False
    tenant_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None  # secret — never logged
    token: str | None = None  # secret — never logged
    ontology_api_name: str | None = None
    test_object_type: str | None = None
    test_object_id: str | None = None
    # Which real client to use when enabled: "rest" (httpx, default) or "sdk" (placeholder).
    client_kind: str = "rest"
    # Optional OAuth2 scopes for the client-credentials grant (space-separated).
    scopes: str | None = None

    @classmethod
    def from_env(cls, env: dict | None = None) -> FoundryConfig:
        env = os.environ if env is None else env
        return cls(
            enabled=_as_bool(env.get("ORCA_FOUNDRY_ENABLED")),
            tenant_url=_get(env, "ORCA_FOUNDRY_TENANT_URL"),
            client_id=_get(env, "ORCA_FOUNDRY_CLIENT_ID"),
            client_secret=_get(env, "ORCA_FOUNDRY_CLIENT_SECRET"),
            token=_get(env, "ORCA_FOUNDRY_TOKEN"),
            ontology_api_name=_get(env, "ORCA_FOUNDRY_ONTOLOGY_API_NAME"),
            test_object_type=_get(env, "ORCA_FOUNDRY_TEST_OBJECT_TYPE"),
            test_object_id=_get(env, "ORCA_FOUNDRY_TEST_OBJECT_ID"),
            client_kind=(_get(env, "ORCA_FOUNDRY_CLIENT") or "rest").lower(),
            scopes=_get(env, "ORCA_FOUNDRY_SCOPES"),
        )

    def base_url(self) -> str | None:
        """Normalised tenant base URL (scheme, no trailing slash). Safe (no secrets)."""
        if not self.tenant_url:
            return None
        url = self.tenant_url if "://" in self.tenant_url else f"https://{self.tenant_url}"
        return url.rstrip("/")

    # --- derived ----------------------------------------------------------------

    def auth_method(self) -> str:
        if self.token:
            return "token"
        if self.client_id and self.client_secret:
            return "client_credentials"
        return "none"

    def safe_host(self) -> str | None:
        """Host only (no path, query, or credentials) — safe to display/log."""
        if not self.tenant_url:
            return None
        parsed = urlparse(self.tenant_url if "://" in self.tenant_url else f"https://{self.tenant_url}")
        return parsed.hostname

    def missing_fields(self) -> list[str]:
        """Required fields that are absent. Only meaningful when ``enabled``."""
        missing: list[str] = []
        if not self.tenant_url:
            missing.append("ORCA_FOUNDRY_TENANT_URL")
        if not self.ontology_api_name:
            missing.append("ORCA_FOUNDRY_ONTOLOGY_API_NAME")
        if self.auth_method() == "none":
            missing.append("ORCA_FOUNDRY_TOKEN or ORCA_FOUNDRY_CLIENT_ID+ORCA_FOUNDRY_CLIENT_SECRET")
        return missing

    def is_configured(self) -> bool:
        return not self.missing_fields()

    def has_secret(self) -> bool:
        return bool(self.client_secret or self.token)

    # --- safe representation (never leaks secrets) ------------------------------

    def safe_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured": self.is_configured(),
            "auth_method": self.auth_method(),
            "client_kind": self.client_kind,
            "host": self.safe_host(),
            "ontology_api_name": self.ontology_api_name,
            "test_object_type": self.test_object_type,
            "test_object_id": self.test_object_id,
            "client_id": _REDACTED if self.client_id else None,
            "client_secret": _REDACTED if self.client_secret else None,
            "token": _REDACTED if self.token else None,
        }

    def __repr__(self) -> str:
        d = self.safe_dict()
        inner = ", ".join(f"{k}={v!r}" for k, v in d.items())
        return f"FoundryConfig({inner})"

    __str__ = __repr__
