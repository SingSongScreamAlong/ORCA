"""Analyst Copilot (v1.0) — local, provider-agnostic, propose-only AI assistance.

AI proposes; analysts decide. Every result is a reviewable proposal with explicit
``generated_by_ai`` / ``requires_human_review`` metadata; nothing becomes authoritative
case material automatically. The default provider is an offline, deterministic mock that
needs no external credentials. Designed to map cleanly to Palantir AIP later (same
propose-only contract) but performs no live external calls. See
``docs/v1.0_aip_assisted_analyst_copilot.md``.
"""

from app.ai_assist.service import AiAssistService

__all__ = ["AiAssistService"]
