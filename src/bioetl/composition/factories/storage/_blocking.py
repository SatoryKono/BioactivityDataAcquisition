"""Async bridge for blocking storage operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

_BlockingResultT = TypeVar("_BlockingResultT")


async def run_storage_blocking(call: Callable[[], _BlockingResultT]) -> _BlockingResultT:
    """Run a blocking storage callable without using the event loop default executor."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="bioetl-storage-io",
    ) as executor:
        return await loop.run_in_executor(executor, call)
