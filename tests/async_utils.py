from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator


async def collect_async_iterator[T](async_iterable: AsyncIterable[T]) -> list[T]:
    """Collect an async iterable into a list with explicit async-next semantics."""
    items: list[T] = []
    async_iter: AsyncIterator[T] = aiter(async_iterable)
    while True:
        try:
            items.append(await anext(async_iter))
        except StopAsyncIteration:
            return items
