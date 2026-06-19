"""Shared schema building blocks."""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

from app.models.enums import ConfidenceBand, band_for

T = TypeVar("T")


class ORCAModel(BaseModel):
    """Base model with shared configuration."""

    model_config = {"from_attributes": True}


# Reusable annotated type for confidence fields across schemas.
ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Strength of evidentiary support in [0, 1]. Not a probability of guilt.",
    ),
]


def confidence_band(value: float) -> ConfidenceBand:
    """Expose the qualitative band for a numeric confidence."""
    return band_for(value)


class Page(ORCAModel, Generic[T]):
    """A simple page of results."""

    items: list[T]
    total: int
    limit: int
    offset: int


class Message(ORCAModel):
    """A simple message response."""

    message: str
