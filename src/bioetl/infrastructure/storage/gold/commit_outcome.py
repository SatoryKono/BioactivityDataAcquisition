"""Observe one physical attempt without retrying an ambiguous commit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace

from bioetl.domain.exceptions.gold_write import GoldWriteCancelled, GoldWriteFailure
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
        await asyncio.shield(task)
    except asyncio.CancelledError as original:
        if not entered:
            task.cancel()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
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
    except Exception as original:
        raise GoldWriteFailure(
            replace(receipt, category=GoldWriteCategory.UNKNOWN)
        ) from original


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
