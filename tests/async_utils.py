from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from typing import TypeVar

_T = TypeVar("_T")


async def collect_async_iterator(async_iterable: AsyncIterable[_T]) -> list[_T]:
    """Collect an async iterable into a list with explicit async-next semantics."""
    items: list[_T] = []
    async_iter: AsyncIterator[_T] = aiter(async_iterable)
    while True:
        try:
            items.append(await anext(async_iter))
        except StopAsyncIteration:
            return items
