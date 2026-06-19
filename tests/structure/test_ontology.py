"""Ontology tests: the machine-readable schema defines every core object and stays in
agreement with the backend enums.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "ontology" / "schema"

CORE_OBJECTS = {
    "observation": "Observation",
    "entity": "Entity",
    "relationship": "Relationship",
    "evidence": "Evidence",
    "source": "Source",
    "cluster": "Cluster",
    "case": "Case",
    "report": "Report",
}


def test_every_core_object_has_a_schema_file():
    for filename, object_name in CORE_OBJECTS.items():
        path = SCHEMA_DIR / f"{filename}.yaml"
        assert path.is_file(), f"missing ontology schema: {filename}.yaml"
        data = yaml.safe_load(path.read_text())
        assert data["object"] == object_name
        assert data["version"] == "0.1"
        assert "properties" in data


def test_observation_is_append_only_and_sourced():
    data = yaml.safe_load((SCHEMA_DIR / "observation.yaml").read_text())
    invariants = " ".join(data["invariants"]).lower()
    assert "append-only" in invariants
    assert "source" in invariants


def test_relationship_requires_supporting_observation():
    data = yaml.safe_load((SCHEMA_DIR / "relationship.yaml").read_text())
    invariants = " ".join(data["invariants"]).lower()
    assert "at least one supporting observation" in invariants


def test_enums_match_backend_entity_types():
    enums = yaml.safe_load((SCHEMA_DIR / "enums.yaml").read_text())
    ontology_entity_types = set(enums["entity_type"]["values"])

    from app.models.enums import EntityType

    backend_entity_types = {e.value for e in EntityType}
    assert ontology_entity_types == backend_entity_types
