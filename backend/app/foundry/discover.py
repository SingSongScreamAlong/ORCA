"""Read-only Foundry discovery helper (v1.2).

Lists the ontologies your credential can see and — when ``ORCA_FOUNDRY_ONTOLOGY_API_NAME``
is set — the object types defined in that ontology, so you can fill in the ontology API name
and discover object-type API names without hand-writing API calls. Reads only metadata (no
object records), loads ``backend/.env`` like the health CLI, and never prints secrets.

    python -m app.foundry.discover
"""

from __future__ import annotations

import json

from app.foundry.client import build_foundry_client
from app.foundry.config import FoundryConfig
from app.foundry.errors import FoundryError
from app.foundry.health import _load_dotenv


def _slim(items: list[dict]) -> list[dict]:
    """Keep only the safe identifying fields (apiName + display name)."""
    return [{"apiName": it.get("apiName"), "displayName": it.get("displayName")} for it in items]


def discover(config: FoundryConfig) -> dict:
    """Return a safe (secret-free) snapshot of ontologies and (optionally) object types."""
    if not config.enabled:
        return {"ok": None, "message": "Foundry integration is disabled (set ORCA_FOUNDRY_ENABLED=true)."}

    client = build_foundry_client(config)
    if not hasattr(client, "list_ontologies"):
        return {
            "ok": False,
            "message": "Discovery requires the REST connector (set ORCA_FOUNDRY_CLIENT=rest).",
        }

    out: dict = {"ok": True, "host": config.safe_host()}
    try:
        out["ontologies"] = _slim(client.list_ontologies())
    except FoundryError as exc:  # messages are written to never contain secrets
        return {"ok": False, "host": config.safe_host(), "message": str(exc)}

    # Object types are listed only when an ontology is configured; a failure here (e.g. a
    # placeholder ontology name) must not hide the ontology listing above.
    if config.ontology_api_name:
        try:
            out["object_types"] = _slim(client.list_object_types())
        except FoundryError as exc:
            out["object_types_error"] = str(exc)

    return out


def main() -> None:
    _load_dotenv()
    print(json.dumps(discover(FoundryConfig.from_env()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
