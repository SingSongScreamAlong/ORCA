"""ORCA → Palantir Foundry ontology mapping (v0.9) — specification + local scaffolding.

This package describes how ORCA's domain model maps onto Foundry object types, link
types, action types, and permission rules, and exports that description as JSON
(``python -m app.foundry_mapping.export``). It makes **no** live Palantir calls and
performs no external I/O beyond writing local files. See
``docs/v0.9_palantir_foundry_mapping.md``.
"""

from app.foundry_mapping.spec import SPEC_VERSION, build_spec

__all__ = ["SPEC_VERSION", "build_spec"]
