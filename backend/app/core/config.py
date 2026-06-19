"""Application configuration, loaded from environment variables.

Settings are read once and cached. Templates live in ``backend/.env.example`` and
``infrastructure/env/.env.example``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Every field maps to an ``ORCA_``-prefixed environment variable.
    """

    model_config = SettingsConfigDict(
        env_prefix="ORCA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    env: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = True
    api_prefix: str = "/api/v1"
    project_name: str = "ORCA"

    # Storage backend selection. "memory" lets the skeleton run with no database.
    storage_backend: Literal["memory", "postgres"] = "memory"

    # PostgreSQL — the system of record.
    postgres_dsn: str = "postgresql+psycopg://orca:orca@localhost:5432/orca"

    # Neo4j — the relationship graph projection.
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "please-change-me"

    # Evidence object store (local path for the skeleton).
    evidence_store: str = "./.evidence"

    # CORS origins permitted to call the API.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def uses_database(self) -> bool:
        return self.storage_backend == "postgres"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
