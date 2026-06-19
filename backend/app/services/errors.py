"""Domain errors raised by the service layer.

The API layer maps these to HTTP responses, keeping HTTP concerns out of the services.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for service-layer errors."""


class NotFoundError(DomainError):
    """A referenced object does not exist."""


class ValidationError(DomainError):
    """A request violates an ontology invariant or other domain rule."""


class PermissionDenied(DomainError):
    """The acting principal lacks the capability required for the operation."""
