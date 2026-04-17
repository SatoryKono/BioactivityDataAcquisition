"""Helpers for deterministic async iterables used in tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class _StaticAsyncIterator(AsyncIterator[T], Generic[T]):
    """Async iterator wrapper around an in-memory iterator."""

    def __init__(self, items: Iterator[T]) -> None:
        self._items = items

    def __aiter__(self) -> _StaticAsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def async_iterable(*items: T) -> AsyncIterator[T]:
    """Return an async iterator that yields the provided items."""

    return _StaticAsyncIterator(iter(items))
