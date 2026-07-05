"""Async bridge for blocking storage operations."""

from __future__ import annotations

from collections.abc import Callable


async def run_storage_blocking[T](call: Callable[[], T]) -> T:
    """Run a blocking storage callable inside the async storage API."""
    return call()
