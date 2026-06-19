"""Minimal task registry for the skeleton.

A real deployment would back this with a queue and scheduler. Here a task is a named
callable, which keeps the worker surface explicit and testable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_REGISTRY: dict[str, Callable[..., Any]] = {}


def task(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a callable as a named task."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _REGISTRY[name] = fn
        return fn

    return decorator


def get_task(name: str) -> Callable[..., Any]:
    return _REGISTRY[name]


def registered_tasks() -> list[str]:
    return sorted(_REGISTRY)
