"""Shared fixtures for backend tests.

Each test starts from a freshly re-seeded in-memory store so tests are independent.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.store import reset_store


@pytest.fixture(autouse=True)
def _fresh_store():
    reset_store()
    yield
    reset_store()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
