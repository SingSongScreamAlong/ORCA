"""Deterministic mock Foundry client (v1.1).

Returns small, **synthetic** data shaped like the ORCA → Foundry ontology (v0.9). No
network, no credentials, no real or sensitive data — so tests are reproducible and the
connection flow can be exercised offline. Read-only.
"""

from __future__ import annotations

from app.foundry.errors import FoundryConnectionError


class MockFoundryClient:
    mode = "mock"

    def __init__(self, *, fail: bool = False) -> None:
        # ``fail=True`` lets tests exercise a simulated connection failure.
        self._fail = fail

    def _guard(self) -> None:
        if self._fail:
            raise FoundryConnectionError("Simulated Foundry connection failure (mock).")

    def health_check(self) -> dict:
        self._guard()
        return {
            "mode": self.mode,
            "reachable": True,
            "ontology": "mock-ontology",
            "note": "Synthetic mock — no real Foundry tenant was contacted.",
        }

    def list_ontologies(self) -> list[dict]:
        self._guard()
        return [{"apiName": "mock-ontology", "displayName": "Mock Ontology (synthetic)"}]

    def list_object_types(self, *, ontology: str | None = None) -> list[dict]:
        self._guard()
        return [
            {"apiName": "OrcaCase", "displayName": "Orca Case"},
            {"apiName": "OrcaEntity", "displayName": "Orca Entity"},
            {"apiName": "OrcaObservation", "displayName": "Orca Observation"},
        ]

    def get_object_type_metadata(self, object_type: str) -> dict:
        self._guard()
        # A small OrcaCase-like shape (synthetic).
        return {
            "apiName": object_type or "OrcaCase",
            "primaryKey": "caseId",
            "properties": [
                {"apiName": "caseId", "baseType": "string"},
                {"apiName": "title", "baseType": "string"},
                {"apiName": "status", "baseType": "string"},
                {"apiName": "createdAt", "baseType": "timestamp"},
            ],
            "synthetic": True,
        }

    def get_object_by_id(self, object_type: str, object_id: str) -> dict:
        self._guard()
        return {
            "apiName": object_type or "OrcaCase",
            "id": object_id or "demo-case-001",
            "properties": {
                "caseId": object_id or "demo-case-001",
                "title": "Synthetic demo case",
                "status": "open",
                "createdAt": "2026-01-01T00:00:00Z",
            },
            "synthetic": True,
        }

    def list_demo_objects(self, object_type: str, limit: int = 10) -> list[dict]:
        self._guard()
        n = max(1, min(limit, 3))
        return [
            {
                "apiName": object_type or "OrcaCase",
                "id": f"demo-case-{i:03d}",
                "properties": {
                    "caseId": f"demo-case-{i:03d}",
                    "title": f"Synthetic demo case {i}",
                    "status": "open",
                },
                "synthetic": True,
            }
            for i in range(1, n + 1)
        ]
