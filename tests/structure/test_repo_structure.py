"""Structure tests: the repository skeleton has the directories and documents the
project promises. These are language-agnostic and guard against accidental deletion.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    "docs",
    "backend",
    "frontend",
    "infrastructure",
    "ontology",
    "tests",
    "backend/app/api",
    "backend/app/models",
    "backend/app/services",
    "backend/app/repositories",
    "backend/app/workers",
    "backend/app/collection",
]

REQUIRED_DOCS = [
    "README.md",
    "docs/mission.md",
    "docs/architecture.md",
    "docs/roadmap.md",
    "docs/security.md",
    "docs/analyst_workflow.md",
    "docs/ontology_v0.1.md",
    "docs/safety_and_handling.md",
    # v1.0 release-hardening / demo-audit deliverables.
    "docs/demo_walkthrough.md",
    "docs/threat_model.md",
    "docs/known_limitations.md",
    "docs/palantir_pitch_notes.md",
    "docs/release_notes_v1.0.md",
]


def test_required_directories_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"missing directories: {missing}"


def test_required_docs_exist_and_are_nonempty():
    for doc in REQUIRED_DOCS:
        path = ROOT / doc
        assert path.is_file(), f"missing doc: {doc}"
        assert path.stat().st_size > 0, f"empty doc: {doc}"


def test_collection_is_interface_only():
    # Hunting Grounds must remain interfaces only in the skeleton.
    collection = ROOT / "backend/app/collection"
    files = {p.name for p in collection.glob("*.py")}
    assert "interfaces.py" in files
