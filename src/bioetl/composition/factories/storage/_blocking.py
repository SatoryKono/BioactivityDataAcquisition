"""Async bridge for blocking storage operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable


async def run_storage_blocking[T](call: Callable[[], T]) -> T:
    """Run a blocking storage callable off the event-loop thread."""
    return await asyncio.to_thread(call)
