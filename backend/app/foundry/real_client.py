"""Real Foundry client — honest scaffolding (v1.1).

This is a *spike*, not a finished integration. The official Palantir Foundry client / OSDK
is **not** a dependency of ORCA, and this milestone deliberately does not guess its API.
This client therefore:

* validates that the integration is enabled and fully configured;
* probes for an optional SDK module (``ORCA_FOUNDRY_SDK_MODULE``, default ``foundry_sdk``);
* fails **gracefully** with a clear, secret-free message when the SDK is absent, pointing
  to ``docs/foundry_connection_setup.md``;
* never writes to Foundry (read-only by design).

When a real SDK is wired in, implement the read-only methods here against it. Until then,
the methods raise a clear error rather than fake Foundry behaviour.
"""

from __future__ import annotations

import importlib.util
import os

from app.foundry.config import FoundryConfig
from app.foundry.errors import (
    FoundryConfigError,
    FoundryConnectionError,
    FoundryDependencyMissing,
    FoundryNotEnabled,
)

_SETUP_DOC = "docs/foundry_connection_setup.md"


class RealFoundryClient:
    mode = "real"

    def __init__(self, config: FoundryConfig) -> None:
        if not config.enabled:
            raise FoundryNotEnabled("Foundry integration is disabled (set ORCA_FOUNDRY_ENABLED=true).")
        missing = config.missing_fields()
        if missing:
            raise FoundryConfigError(
                "Foundry is enabled but configuration is incomplete: missing "
                + ", ".join(missing)
                + f". See {_SETUP_DOC}."
            )
        self.config = config

    def _sdk_module_name(self) -> str:
        return os.environ.get("ORCA_FOUNDRY_SDK_MODULE", "foundry_sdk")

    def _require_sdk(self):
        module = self._sdk_module_name()
        if importlib.util.find_spec(module) is None:
            raise FoundryDependencyMissing(
                f"The Palantir Foundry SDK ('{module}') is not installed. The v1.1 spike "
                "ships the connection abstraction and a mock client only; install and wire "
                f"the official OSDK/SDK to enable real read-only calls. See {_SETUP_DOC}."
            )
        return importlib.import_module(module)

    def _not_implemented(self, what: str):
        # SDK is present but the spike intentionally does not guess its API surface.
        raise FoundryConnectionError(
            f"Real Foundry {what} is not implemented in the v1.1 spike. Wire the installed "
            f"SDK ('{self._sdk_module_name()}') here to enable read-only access. See {_SETUP_DOC}."
        )

    # --- read-only methods -------------------------------------------------------

    def health_check(self) -> dict:
        self._require_sdk()
        self._not_implemented("health check")

    def get_object_type_metadata(self, object_type: str) -> dict:
        self._require_sdk()
        self._not_implemented("object-type metadata read")

    def get_object_by_id(self, object_type: str, object_id: str) -> dict:
        self._require_sdk()
        self._not_implemented("object read")

    def list_demo_objects(self, object_type: str, limit: int = 10) -> list[dict]:
        self._require_sdk()
        self._not_implemented("object listing")
