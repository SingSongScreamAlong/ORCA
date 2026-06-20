"""ORCA → Palantir Foundry connection layer (v1.1 — connection spike).

ORCA is *Palantir-ready* (v0.9 mapping/spec) and this milestone takes the smallest safe
step toward *Palantir-connected*: a configuration shape, a read-only client abstraction, a
deterministic mock client, honest real-client scaffolding, and a secret-free health check.
Disabled by default; no live calls and no credentials are required to run the tests. See
``docs/v1.1_foundry_connection_spike.md`` and ``docs/foundry_connection_setup.md``.
"""

from app.foundry.client import FoundryClient, build_foundry_client
from app.foundry.config import FoundryConfig

# Note: ``foundry_health`` lives in ``app.foundry.health`` and is imported from there
# directly (importing it here would double-import under ``python -m app.foundry.health``).

__all__ = ["FoundryClient", "FoundryConfig", "build_foundry_client"]
