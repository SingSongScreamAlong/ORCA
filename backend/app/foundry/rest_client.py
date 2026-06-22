"""REST Foundry client (v1.2) — a real, read-only connector over httpx.

Talks to a Foundry tenant's documented v2 platform API. Read-only: only ``GET`` requests
(plus the OAuth2 token exchange) are issued — there is no write path. Authentication is
either a pre-issued bearer token (``ORCA_FOUNDRY_TOKEN``) or the OAuth2 **client
credentials** grant (``ORCA_FOUNDRY_CLIENT_ID`` + ``ORCA_FOUNDRY_CLIENT_SECRET``).

Secrets are never placed in error messages or logs. The first connectivity proof is the
ontology-metadata listing (``GET /api/v2/ontologies``), which reads no records.

Endpoint paths follow Foundry's public v2 API; verify scope names and exact paths against
your tenant's API docs (see ``docs/foundry_connection_setup.md``). The connector is
disabled by default and is never exercised against a live tenant in tests — tests inject a
mock transport.
"""

from __future__ import annotations

from typing import Any

from app.foundry.config import FoundryConfig
from app.foundry.errors import (
    FoundryConfigError,
    FoundryConnectionError,
    FoundryNotEnabled,
)

_TIMEOUT = 30.0


class RestFoundryClient:
    mode = "real"

    def __init__(self, config: FoundryConfig, *, http_client: Any | None = None) -> None:
        if not config.enabled:
            raise FoundryNotEnabled("Foundry integration is disabled (set ORCA_FOUNDRY_ENABLED=true).")
        missing = config.missing_fields()
        if missing:
            raise FoundryConfigError(
                "Foundry is enabled but configuration is incomplete: missing "
                + ", ".join(missing)
                + ". See docs/foundry_connection_setup.md."
            )
        self.config = config
        self._http = http_client  # injectable httpx.Client for tests
        self._cached_token: str | None = None

    # --- transport ---------------------------------------------------------------

    def _client(self):
        if self._http is not None:
            return self._http
        import httpx

        self._http = httpx.Client(timeout=_TIMEOUT)
        return self._http

    def _bearer_token(self) -> str:
        """Return a bearer token: a pre-issued one, or one from the client-credentials grant."""
        if self.config.token:
            return self.config.token
        if self._cached_token:
            return self._cached_token

        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        if self.config.scopes:
            data["scope"] = self.config.scopes
        url = f"{self.config.base_url()}/multipass/api/oauth2/token"
        try:
            resp = self._client().post(
                url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        except Exception as exc:  # noqa: BLE001 — surfaced as a safe connection error
            raise FoundryConnectionError("Token request to Foundry failed (network error).") from exc
        if resp.status_code >= 400:
            # Never echo the request (it carries the client secret) — only a safe summary.
            raise FoundryConnectionError(
                f"OAuth2 token request was rejected (HTTP {resp.status_code}). "
                "Check ORCA_FOUNDRY_CLIENT_ID/SECRET and scopes."
            )
        token = (resp.json() or {}).get("access_token")
        if not token:
            raise FoundryConnectionError("OAuth2 token response did not contain an access_token.")
        self._cached_token = token
        return token

    def _get(self, path: str, params: dict | None = None) -> dict:
        token = self._bearer_token()
        url = f"{self.config.base_url()}/{path.lstrip('/')}"
        try:
            resp = self._client().get(
                url, headers={"Authorization": f"Bearer {token}"}, params=params
            )
        except Exception as exc:  # noqa: BLE001
            raise FoundryConnectionError(f"GET {path} to Foundry failed (network error).") from exc
        if resp.status_code >= 400:
            raise FoundryConnectionError(
                f"Foundry read failed: GET {path} returned HTTP {resp.status_code}."
            )
        return resp.json() or {}

    # --- read-only methods -------------------------------------------------------

    def health_check(self) -> dict:
        # Lowest-risk connectivity proof: list ontologies (reads no object records).
        data = self._get("api/v2/ontologies")
        ontologies = data.get("data", data if isinstance(data, list) else [])
        return {
            "mode": self.mode,
            "reachable": True,
            "ontology_count": len(ontologies) if isinstance(ontologies, list) else None,
            "note": "Read-only ontology metadata listing; no records were read.",
        }

    def get_object_type_metadata(self, object_type: str) -> dict:
        ont = self._require_ontology()
        return self._get(f"api/v2/ontologies/{ont}/objectTypes/{object_type}")

    def get_object_by_id(self, object_type: str, object_id: str) -> dict:
        ont = self._require_ontology()
        return self._get(f"api/v2/ontologies/{ont}/objects/{object_type}/{object_id}")

    def list_demo_objects(self, object_type: str, limit: int = 10) -> list[dict]:
        ont = self._require_ontology()
        data = self._get(
            f"api/v2/ontologies/{ont}/objects/{object_type}", params={"pageSize": max(1, limit)}
        )
        items = data.get("data", [])
        return items if isinstance(items, list) else []

    def _require_ontology(self) -> str:
        if not self.config.ontology_api_name:
            raise FoundryConfigError("ORCA_FOUNDRY_ONTOLOGY_API_NAME is required for object reads.")
        return self.config.ontology_api_name
