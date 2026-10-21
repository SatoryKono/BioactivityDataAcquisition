"""Observe one physical attempt without retrying an ambiguous commit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from types import TracebackType
from typing import Literal

from bioetl.domain.exceptions.gold_write import (
    GoldWriteCancelled as DomainGoldWriteCancelled,
)
from bioetl.domain.exceptions.gold_write import (
    GoldWriteFailure,
    GoldWriteValidationFailure,
)
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt
from bioetl.infrastructure.storage.gold.cancellation import (
    GoldWriteCancelled as GoldWriteCancelled,
)
from bioetl.infrastructure.storage.gold.cancellation import (
    _PhysicalCancellationBoundary,
)


async def await_physical_commit(
    operation: Callable[[], Awaitable[object]], receipt: GoldWriteReceipt
) -> None:
    """Observe one physical attempt and propagate cancellation after its cleanup."""
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
    async with _PhysicalCancellationBoundary(task, receipt, lambda: entered):
        with GoldOutcomeBoundary(
            replace(receipt, category=GoldWriteCategory.UNKNOWN),
            propagate_cancellation=True,
        ):
            await asyncio.shield(task)


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


class GoldOutcomeBoundary:
    """Observe a write phase without mutating an original or frozen exception."""

    def __init__(
        self,
        receipt: GoldWriteReceipt | Callable[[BaseException], GoldWriteReceipt],
        *,
        preserve_outcome: bool = False,
        propagate_cancellation: bool = False,
        flatten_cause: bool = False,
        translate_failure: bool = True,
    ) -> None:
        self._receipt = receipt
        self._preserve_outcome = preserve_outcome
        self._propagate_cancellation = propagate_cancellation
        self._flatten_cause = flatten_cause
        self._translate_failure = translate_failure

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        original: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if isinstance(original, DomainGoldWriteCancelled) and not isinstance(
            original, asyncio.CancelledError
        ):
            raise GoldWriteCancelled(original.receipt) from (
                original.__cause__ or original
            )
        if original is None or not isinstance(
            original, (Exception, asyncio.CancelledError)
        ):
            return False
        if self._should_propagate(original):
            return False
        receipt = self._receipt(original) if callable(self._receipt) else self._receipt
        cause = _failure_cause(original, self._flatten_cause)
        if isinstance(original, asyncio.CancelledError):
            raise GoldWriteCancelled(receipt) from cause
        raise _failure_for(receipt, cause) from cause

    def _should_propagate(self, original: BaseException) -> bool:
        """Keep cancellation, ordinary validation and classified outcomes intact."""
        return (
            (
                self._propagate_cancellation
                and isinstance(original, asyncio.CancelledError)
            )
            or (not self._translate_failure and isinstance(original, Exception))
            or (
                self._preserve_outcome
                and isinstance(original, (GoldWriteFailure, GoldWriteCancelled))
            )
        )


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


def _failure_cause(original: BaseException, flatten: bool) -> BaseException:
    """Flatten only classified Gold outcomes, preserving the original otherwise."""
    cause: BaseException = original
    if flatten and isinstance(original, (GoldWriteFailure, GoldWriteCancelled)):
        cause = original.__cause__ or original
    return cause
