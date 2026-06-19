"""Repository helpers shared across the in-memory repositories."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def paginate(items: Iterable[T], *, limit: int, offset: int) -> list[T]:
    """Return a slice of ``items`` for simple offset/limit pagination."""
    ordered = list(items)
    return ordered[offset : offset + limit]


def newest_first(items: Iterable[T], key: str = "created_at") -> list[T]:
    """Return ``items`` sorted by a timestamp attribute, newest first."""
    return sorted(items, key=lambda obj: getattr(obj, key), reverse=True)
