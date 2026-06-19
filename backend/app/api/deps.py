"""Shared API dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from app.core.security import Principal, get_current_principal


def current_principal() -> Principal:
    """FastAPI dependency returning the authenticated principal.

    Backed by the development principal until authentication lands (see
    ``app.core.security``).
    """
    return get_current_principal()


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return."),
    offset: int = Query(0, ge=0, description="Items to skip."),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
