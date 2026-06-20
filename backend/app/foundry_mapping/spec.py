"""Assemble the full ORCA → Foundry ontology specification (v0.9)."""

from __future__ import annotations

from app.foundry_mapping.actions import ACTION_TYPES, FORBIDDEN_WORKFLOWS, INVARIANTS
from app.foundry_mapping.links import LINK_TYPES
from app.foundry_mapping.objects import OBJECT_TYPES
from app.foundry_mapping.permissions import CASE_ROLE_PERMISSIONS
from app.foundry_mapping.types import OntologySpec

SPEC_VERSION = "0.9.0"


def build_spec() -> OntologySpec:
    return OntologySpec(
        version=SPEC_VERSION,
        objects=OBJECT_TYPES,
        links=LINK_TYPES,
        actions=ACTION_TYPES,
        permissions=CASE_ROLE_PERMISSIONS,
        forbidden_workflows=FORBIDDEN_WORKFLOWS,
        invariants=INVARIANTS,
    )
