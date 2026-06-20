"""Export the ORCA → Foundry ontology mapping to local JSON.

    python -m app.foundry_mapping.export [output_dir]

Writes deterministic, sorted JSON (no live Palantir calls) to ``<output_dir>``, default
``foundry/`` at the repository root:

* ``object_types.json``  — Foundry object types and property mappings
* ``link_types.json``    — Foundry link types
* ``action_types.json``  — Foundry action types (with RBAC/case gates and invariants)
* ``permissions.json``   — case-role permission rules (derived from ORCA's RBAC)
* ``ontology_spec.json`` — the complete spec, plus forbidden workflows and invariants
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.foundry_mapping.spec import build_spec
from app.foundry_mapping.types import to_dict

# repo root = backend/app/foundry_mapping/export.py -> parents[3]
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "foundry"


def _dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export(output_dir: Path | None = None) -> list[Path]:
    out = output_dir or _DEFAULT_OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    spec = build_spec()

    files = {
        "object_types.json": [to_dict(o) for o in spec.objects],
        "link_types.json": [to_dict(link) for link in spec.links],
        "action_types.json": [to_dict(a) for a in spec.actions],
        "permissions.json": {
            "case_roles": [to_dict(p) for p in spec.permissions],
        },
        "ontology_spec.json": {
            "version": spec.version,
            "objects": [to_dict(o) for o in spec.objects],
            "links": [to_dict(link) for link in spec.links],
            "actions": [to_dict(a) for a in spec.actions],
            "permissions": [to_dict(p) for p in spec.permissions],
            "forbidden_workflows": list(spec.forbidden_workflows),
            "invariants": list(spec.invariants),
        },
    }
    written: list[Path] = []
    for name, payload in files.items():
        path = out / name
        _dump(path, payload)
        written.append(path)
    return written


def main() -> None:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    written = export(target)
    print(f"Wrote {len(written)} mapping file(s):")
    for path in written:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
