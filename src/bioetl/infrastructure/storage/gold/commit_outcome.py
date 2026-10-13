"""Observe one physical attempt without retrying an ambiguous commit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Literal

from bioetl.domain.exceptions.gold_write import (
    GoldWriteCancelled as DomainGoldWriteCancelled,
)
from bioetl.domain.exceptions.gold_write import (
    GoldWriteFailure,
)
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt


class GoldWriteCancelled(asyncio.CancelledError, DomainGoldWriteCancelled):
    """Adapt the domain receipt to the asyncio cancellation hierarchy."""

    def __init__(self, receipt: GoldWriteReceipt) -> None:
        DomainGoldWriteCancelled.__init__(self, receipt)


class GoldOutcomeBoundary:
    """Translate stage errors to receipts without mutating the original error.

    This synchronous boundary keeps the operation on its caller's task. Process
    control exceptions pass through; asyncio cancellation retains its hierarchy.
    """

    def __init__(
        self, receipt: GoldWriteReceipt, *, translate_failure: bool = True
    ) -> None:
        self.receipt = receipt
        self.translate_failure = translate_failure

    def __enter__(self) -> GoldOutcomeBoundary:
        return self

    def __exit__(
        self, error_type: object, error: BaseException | None, traceback: object
    ) -> Literal[False]:
        if isinstance(error, DomainGoldWriteCancelled):
            if not isinstance(error, asyncio.CancelledError):
                raise GoldWriteCancelled(error.receipt) from (error.__cause__ or error)
            return False
        if isinstance(error, GoldWriteFailure):
            return False
        if isinstance(error, asyncio.CancelledError):
            raise GoldWriteCancelled(self.receipt) from error
        if self.translate_failure and isinstance(error, Exception):
            raise GoldWriteFailure(self.receipt) from error
        return False


async def await_physical_commit(
    operation: Callable[[], Awaitable[object]], receipt: GoldWriteReceipt
) -> None:
    """Drain a started thread on cancellation; never report an unobserved commit."""
    current = asyncio.current_task()
    if current is not None and current.cancelling():
        raise GoldWriteCancelled(
            replace(
                receipt, category=GoldWriteCategory.NOT_COMMITTED, committed_targets=()
            )
        ) from asyncio.CancelledError()
    entered = False

    async def attempt() -> object:
        nonlocal entered
        entered = True
        return await operation()

    task = asyncio.create_task(attempt())
    try:
        (result,) = await asyncio.shield(asyncio.gather(task, return_exceptions=True))
    except asyncio.CancelledError as original:
        if not entered:
            task.cancel()
        try:
            await _drain_physical_attempt(task)
        finally:
            category = (
                GoldWriteCategory.NOT_COMMITTED
                if not entered
                else GoldWriteCategory.UNKNOWN
            )
            if task.done() and not task.cancelled() and task.exception() is None:
                category = GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
            targets = (
                (receipt.physical_table,)
                if category == GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
                else ()
            )
            raise GoldWriteCancelled(
                replace(receipt, category=category, committed_targets=targets)
            ) from original
    if task.cancelled():
        raise GoldWriteCancelled(
            replace(receipt, category=GoldWriteCategory.UNKNOWN)
        ) from (result if isinstance(result, BaseException) else None)
    error = task.exception()
    if error is not None:
        raise GoldWriteFailure(
            replace(receipt, category=GoldWriteCategory.UNKNOWN)
        ) from error


class _DeferredCancellation:
    """Keep the last cancellation until the physical cleanup has completed."""

    def __init__(self) -> None:
        self.error: asyncio.CancelledError | None = None

    def __enter__(self) -> None:
        return None

    def __exit__(
        self, error_type: object, error: BaseException | None, traceback: object
    ) -> bool:
        if isinstance(error, asyncio.CancelledError):
            self.error = error
            return True
        return False


async def _drain_physical_attempt(task: asyncio.Task[object]) -> None:
    """Defer repeated cancellation without recursion, then propagate it."""
    deferred = _DeferredCancellation()
    while not task.done():
        with deferred:
            await asyncio.wait((task,))
    if deferred.error is not None:
        raise deferred.error


def receipt_for(
    table: str,
    version: str = "0.0.0",
    category: GoldWriteCategory = GoldWriteCategory.NOT_COMMITTED,
) -> GoldWriteReceipt:
    return GoldWriteReceipt(
        table,
        version,
        category,
        (table,)
        if category
        in (GoldWriteCategory.COMPLETE, GoldWriteCategory.COMMITTED_POSTWRITE_PENDING)
        else (),
    )
