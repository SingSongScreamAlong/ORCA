"""Foundry read-only health/diagnostic check (v1.1).

Reports whether the integration is enabled, configured, and (if enabled) reachable —
**without ever emitting secrets**. Usable as a library call, an admin API endpoint, or a
CLI:

    python -m app.foundry.health

This is an admin/connection diagnostic, not a case action, so it is **not** written to the
case audit log (see ``docs/v1.1_foundry_connection_spike.md``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.foundry.client import FoundryClient, build_foundry_client
from app.foundry.config import FoundryConfig
from app.foundry.errors import FoundryError


def foundry_health(config: FoundryConfig, client: FoundryClient | None = None) -> dict:
    """Return a safe (secret-free) health snapshot for the Foundry integration."""
    base = config.safe_dict()  # already redacts secrets
    if client is not None:
        base["mode"] = getattr(client, "mode", "unknown")
    elif config.enabled:
        base["mode"] = "real"
    else:
        base["mode"] = "disabled"

    if not config.enabled and client is None:
        return {**base, "ok": None, "message": "Foundry integration is disabled."}

    missing = config.missing_fields()
    if config.enabled and missing and client is None:
        return {
            **base,
            "ok": False,
            "errors": missing,
            "message": "Foundry is enabled but configuration is incomplete.",
        }

    try:
        active = client or build_foundry_client(config)
        base["mode"] = getattr(active, "mode", base["mode"])
        result = active.health_check()
        return {**base, "ok": True, "result": result, "message": "Foundry read-only check OK."}
    except FoundryError as exc:
        # Error messages are written to never contain secrets.
        return {**base, "ok": False, "message": str(exc)}


def _load_dotenv() -> None:
    """Best-effort load of a local ``.env`` into ``os.environ`` for the CLI.

    ``FoundryConfig.from_env()`` reads ``os.environ``; when this command is run from
    ``backend/`` with credentials in ``backend/.env``, those vars would otherwise be invisible.
    Real environment variables already set are **not** overridden (CI/production win), and a
    missing file is simply a no-op. Values are parsed literally — no shell expansion, no
    secrets logged.
    """
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    seen: set[str] = set()
    for env_path in candidates:
        key = str(env_path)
        if key in seen or not env_path.is_file():
            continue
        seen.add(key)
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name and name not in os.environ:
                os.environ[name] = value


def main() -> None:
    _load_dotenv()
    config = FoundryConfig.from_env()
    print(json.dumps(foundry_health(config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
