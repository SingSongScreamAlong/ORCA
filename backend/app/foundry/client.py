"""Foundry client abstraction (v1.1) — read-only methods only.

This milestone is a connection *spike*: the only client that actually returns data is the
deterministic ``MockFoundryClient``. The real client is honest scaffolding that fails
gracefully with clear guidance when its SDK/credentials are absent (see ``real_client``).
No method writes to Foundry.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.foundry.config import FoundryConfig
from app.foundry.errors import FoundryNotEnabled


@runtime_checkable
class FoundryClient(Protocol):
    mode: str  # "mock" | "real"

    def health_check(self) -> dict: ...
    def get_object_type_metadata(self, object_type: str) -> dict: ...
    def get_object_by_id(self, object_type: str, object_id: str) -> dict: ...
    def list_demo_objects(self, object_type: str, limit: int = 10) -> list[dict]: ...


def build_foundry_client(config: FoundryConfig, *, allow_mock_fallback: bool = True) -> FoundryClient:
    """Construct a client for the active configuration.

    * enabled + ``client_kind == "rest"`` (default) → the real REST connector (httpx);
    * enabled + ``client_kind == "sdk"`` → the SDK placeholder (fails gracefully if absent);
    * disabled → the mock client (so local dev/tests work with no credentials), unless
      ``allow_mock_fallback=False``.
    """
    if config.enabled:
        if config.client_kind == "sdk":
            from app.foundry.real_client import RealFoundryClient

            return RealFoundryClient(config)
        from app.foundry.rest_client import RestFoundryClient

        return RestFoundryClient(config)
    if allow_mock_fallback:
        from app.foundry.mock_client import MockFoundryClient

        return MockFoundryClient()
    raise FoundryNotEnabled("Foundry integration is disabled (set ORCA_FOUNDRY_ENABLED=true).")
