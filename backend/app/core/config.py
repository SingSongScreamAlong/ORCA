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

    # Dev authentication: the user assumed when no X-ORCA-User header is supplied.
    # Suitable for local/dev only; production replaces this with real authentication.
    dev_default_user: str = "admin"

    # PostgreSQL — the system of record.
    postgres_dsn: str = "postgresql+psycopg://orca:orca@localhost:5432/orca"

    # Neo4j — the relationship graph projection.
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "please-change-me"
    # The graph projection is optional; PostgreSQL is authoritative. Enable to mirror
    # entities/relationships into Neo4j.
    graph_enabled: bool = False

    # Evidence object store (local path for the skeleton).
    evidence_store: str = "./.evidence"

    # Evidence file upload (v0.7) — safe-by-default manual upload policy.
    # Maximum accepted upload size in bytes (default 25 MiB). Oversize uploads are rejected.
    evidence_max_upload_bytes: int = 26_214_400
    # Allow-list of MIME types stored as normal evidence. Anything not allowed (and not
    # blocked) is stored *quarantined* pending review. Conservative by default.
    evidence_allowed_mime_types: str = (
        "application/pdf,image/png,image/jpeg,image/gif,image/webp,image/tiff,"
        "text/plain,text/csv,text/markdown,application/json"
    )
    # File extensions that are refused outright (never stored) — executables and scripts.
    evidence_blocked_extensions: str = (
        ".exe,.dll,.so,.dylib,.sh,.bash,.bat,.cmd,.ps1,.psm1,.js,.mjs,.jar,.msi,.scr,"
        ".com,.bin,.app,.deb,.rpm,.apk,.dmg,.vbs,.wsf"
    )
    # Whether case viewers may download approved raw bytes (default off — viewers see
    # metadata only; mutating roles and admins always may). "Policy explicitly allows."
    evidence_allow_viewer_download: bool = False

    # Analyst Copilot (v1.0). The default "mock" provider is offline and deterministic and
    # needs no credentials; AI output is always proposed-only and human-reviewed.
    ai_provider: str = "mock"

    @property
    def evidence_allowed_mime_set(self) -> set[str]:
        return {m.strip().lower() for m in self.evidence_allowed_mime_types.split(",") if m.strip()}

    @property
    def evidence_blocked_extension_set(self) -> set[str]:
        return {
            (e if e.startswith(".") else f".{e}").strip().lower()
            for e in self.evidence_blocked_extensions.split(",")
            if e.strip()
        }

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
