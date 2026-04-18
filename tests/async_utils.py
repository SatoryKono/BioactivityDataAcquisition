from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TypeVar

_T = TypeVar("_T")


async def collect_async_iterator(async_iter: AsyncIterator[_T]) -> list[_T]:
    """Collect an async iterator into a list with explicit async-next semantics."""
    items: list[_T] = []
    while True:
        try:
            items.append(await anext(async_iter))
        except StopAsyncIteration:
            return items
