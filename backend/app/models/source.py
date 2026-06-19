"""Source ORM model — where an observation came from."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.enums import SourceReliability, SourceType
from app.models.types import pg_enum


class Source(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "sources"

    source_type: Mapped[SourceType] = mapped_column(
        pg_enum(SourceType, "source_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    reliability: Mapped[SourceReliability] = mapped_column(
        pg_enum(SourceReliability, "source_reliability"),
        nullable=False,
        default=SourceReliability.UNKNOWN,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
