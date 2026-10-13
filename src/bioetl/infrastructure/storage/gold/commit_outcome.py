"""Observe one physical attempt without retrying an ambiguous commit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from types import TracebackType
from typing import Literal

from bioetl.domain.exceptions.gold_write import (
    GoldWriteFailure,
    GoldWriteValidationFailure,
)
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt


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
        with GoldOutcomeBoundary(
            replace(receipt, category=GoldWriteCategory.UNKNOWN),
            propagate_cancellation=True,
        ):
            await asyncio.shield(task)
    except asyncio.CancelledError as original:
        if not entered:
            task.cancel()
        await _drain_physical_attempt(task)
        category = (
            GoldWriteCategory.NOT_COMMITTED
            if not entered
            else GoldWriteCategory.UNKNOWN
        )
        if not task.cancelled() and task.exception() is None:
            category = GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
        targets = (
            (receipt.physical_table,)
            if category == GoldWriteCategory.COMMITTED_POSTWRITE_PENDING
            else ()
        )
        raise GoldWriteCancelled(
            replace(receipt, category=category, committed_targets=targets)
        ) from original


async def _drain_physical_attempt(task: asyncio.Task[object]) -> None:
    """Observe the started attempt despite repeated caller cancellation."""
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            continue


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


class GoldWriteCancelled(asyncio.CancelledError):
    """Preserve asyncio cancellation and an independently classified receipt."""

    def __init__(
        self,
        receipt: GoldWriteReceipt,
        *,
        diagnostic_error: BaseException | None = None,
    ) -> None:
        self.receipt = receipt
        self.diagnostic_error = diagnostic_error
        super().__init__(
            f"Gold write cancelled: {receipt.physical_table}: {receipt.category}"
        )


class GoldOutcomeBoundary:
    """Observe a write phase without mutating an original or frozen exception."""

    def __init__(
        self,
        receipt: GoldWriteReceipt | Callable[[BaseException], GoldWriteReceipt],
        *,
        preserve_outcome: bool = False,
        propagate_cancellation: bool = False,
        flatten_cause: bool = False,
    ) -> None:
        self._receipt = receipt
        self._preserve_outcome = preserve_outcome
        self._propagate_cancellation = propagate_cancellation
        self._flatten_cause = flatten_cause

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        original: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if original is None or not isinstance(
            original, (Exception, asyncio.CancelledError)
        ):
            return False
        if self._propagate_cancellation and isinstance(
            original, asyncio.CancelledError
        ):
            return False
        if self._preserve_outcome and isinstance(
            original, (GoldWriteFailure, GoldWriteCancelled)
        ):
            return False
        receipt = self._receipt(original) if callable(self._receipt) else self._receipt
        cause: BaseException = original
        if self._flatten_cause and isinstance(
            original, (GoldWriteFailure, GoldWriteCancelled)
        ):
            cause = original.__cause__ or original
        if isinstance(original, asyncio.CancelledError):
            raise GoldWriteCancelled(receipt) from cause
        raise _failure_for(receipt, cause) from cause


class GoldDiagnosticsBoundary:
    """Keep primary outcome and cause when secondary failure diagnostics fail."""

    def __init__(self, primary: BaseException, receipt: GoldWriteReceipt) -> None:
        self._primary = primary
        self._receipt = receipt

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        diagnostic: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if diagnostic is None or not isinstance(
            diagnostic, (Exception, asyncio.CancelledError)
        ):
            return False
        primary = self._primary
        cause = (
            primary.__cause__ or primary
            if isinstance(primary, (GoldWriteFailure, GoldWriteCancelled))
            else primary
        )
        cancelled = isinstance(primary, asyncio.CancelledError) or isinstance(
            diagnostic, asyncio.CancelledError
        )
        if cancelled:
            raise GoldWriteCancelled(
                self._receipt, diagnostic_error=diagnostic
            ) from cause
        raise _failure_for(self._receipt, cause, diagnostic) from cause


def _failure_for(
    receipt: GoldWriteReceipt,
    cause: BaseException,
    diagnostic: BaseException | None = None,
) -> GoldWriteFailure:
    """Validation is noncritical only when no target has a proven commit."""
    if (
        receipt.category == GoldWriteCategory.NOT_COMMITTED
        and not receipt.committed_targets
        and isinstance(cause, ValueError)
    ):
        return GoldWriteValidationFailure(receipt, cause, diagnostic_error=diagnostic)
    return GoldWriteFailure(receipt, diagnostic_error=diagnostic)
