"""Helpers for deterministic async iterables used in tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator


class _StaticAsyncIterator[T](AsyncIterator[T]):
    """Async iterator wrapper around an in-memory iterator."""

    def __init__(self, items: Iterator[T]) -> None:
        self._items = items

    def __aiter__(self) -> _StaticAsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        await asyncio.sleep(0)
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def async_iterable[T](*items: T) -> AsyncIterator[T]:
    """Return an async iterator that yields the provided items."""

    return _StaticAsyncIterator(iter(items))


class _FailingAsyncIterator[T](AsyncIterator[T]):
    """Async iterator that raises the provided error on first iteration."""

    def __init__(self, error: BaseException) -> None:
        self._error = error

    def __aiter__(self) -> _FailingAsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        await asyncio.sleep(0)
        raise self._error


def failing_async_iterable[T](error: BaseException) -> AsyncIterator[T]:
    """Return an async iterator that raises ``error`` when iterated."""

    return _FailingAsyncIterator(error)
