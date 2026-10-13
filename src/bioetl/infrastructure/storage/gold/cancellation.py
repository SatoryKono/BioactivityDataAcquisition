"""Async cancellation transport and bounded-memory physical-outcome observation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import Literal

from bioetl.domain.exceptions.gold_write import (
    GoldWriteCancelled as DomainGoldWriteCancelled,
)
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt


class GoldWriteCancelled(asyncio.CancelledError, DomainGoldWriteCancelled):
    """Preserve asyncio cancellation and an independently classified receipt."""

    def __init__(
        self,
        receipt: GoldWriteReceipt,
        *,
        diagnostic_error: BaseException | None = None,
    ) -> None:
        self.receipt = receipt
        self.diagnostic_error = diagnostic_error
        DomainGoldWriteCancelled.__init__(self, receipt)


class _DeferredCancellation:
    """Delay only cancellation until a started physical task has been observed."""

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


class _PhysicalCancellationBoundary:
    """Retain the original cancellation while finishing physical-outcome observation."""

    def __init__(
        self,
        task: asyncio.Task[object],
        receipt: GoldWriteReceipt,
        entered: Callable[[], bool],
    ) -> None:
        self.task, self.receipt, self.entered = task, receipt, entered

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self, error_type: object, original: BaseException | None, traceback: object
    ) -> Literal[False]:
        if not isinstance(original, asyncio.CancelledError):
            return False
        entered = self.entered()
        if not entered:
            self.task.cancel()
        with _DeferredCancellation():
            await _drain_physical_attempt(self.task)
        category = (
            GoldWriteCategory.NOT_COMMITTED
            if not entered
            else GoldWriteCategory.UNKNOWN
        )
        if (
            self.task.done()
            and not self.task.cancelled()
            and self.task.exception() is None
        ):
            category = GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
        targets = (
            (self.receipt.physical_table,)
            if category == GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
            else ()
        )
        raise GoldWriteCancelled(
            replace(self.receipt, category=category, committed_targets=targets)
        ) from original


async def _drain_physical_attempt(task: asyncio.Task[object]) -> None:
    """Drain repeated cancellation in constant stack depth, then propagate it."""
    deferred = _DeferredCancellation()
    while not task.done():
        with deferred:
            await asyncio.wait((task,))
    if deferred.error is not None:
        raise deferred.error
