"""Evidence content store — the integrity layer.

Evidence *metadata* lives in the system of record; evidence *bytes* (when available)
are stored here, content-addressed by SHA-256. The hash is the integrity anchor: a
verify re-reads the bytes and re-hashes them, surfacing any mismatch.

Two implementations:

* ``InMemoryContentStore`` — bytes held in a process dict (development / tests).
* ``FilesystemContentStore`` — bytes written under ``ORCA_EVIDENCE_STORE`` keyed by hash.

The store never decodes, renders, or inspects content. It only hashes and stores bytes.
It must never be used for material prohibited by docs/safety_and_handling.md.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


class ContentStore(Protocol):
    def put(self, data: bytes) -> str: ...
    def get(self, sha256: str) -> bytes | None: ...
    def exists(self, sha256: str) -> bool: ...


class InMemoryContentStore:
    """Process-wide content store backed by a dict (development / tests)."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put(self, data: bytes) -> str:
        digest = sha256_hex(data)
        self._blobs[digest] = data
        return digest

    def get(self, sha256: str) -> bytes | None:
        return self._blobs.get(sha256)

    def exists(self, sha256: str) -> bool:
        return sha256 in self._blobs

    def clear(self) -> None:
        self._blobs.clear()


class FilesystemContentStore:
    """Content store that writes bytes under a base directory, keyed by hash."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, sha256: str) -> Path:
        return self._base / sha256

    def put(self, data: bytes) -> str:
        digest = sha256_hex(data)
        path = self._path(digest)
        if not path.exists():
            path.write_bytes(data)
        return digest

    def get(self, sha256: str) -> bytes | None:
        path = self._path(sha256)
        return path.read_bytes() if path.exists() else None

    def exists(self, sha256: str) -> bool:
        return self._path(sha256).exists()


# Process-wide in-memory content store for the development backend.
memory_content_store = InMemoryContentStore()


def build_content_store() -> ContentStore:
    """Return the content store for the active storage backend."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.uses_database:
        return FilesystemContentStore(settings.evidence_store)
    return memory_content_store
