"""Errors for the Foundry connection layer (v1.1).

These never carry secret values in their messages — only safe, actionable guidance.
"""

from __future__ import annotations


class FoundryError(Exception):
    """Base class for Foundry connection errors."""


class FoundryNotEnabled(FoundryError):
    """Raised when a real connection is attempted while the integration is disabled."""


class FoundryConfigError(FoundryError):
    """Raised when the integration is enabled but required configuration is missing."""


class FoundryDependencyMissing(FoundryError):
    """Raised when the real client is requested but its SDK dependency is not installed."""


class FoundryConnectionError(FoundryError):
    """Raised when a read-only connection attempt fails at runtime."""
