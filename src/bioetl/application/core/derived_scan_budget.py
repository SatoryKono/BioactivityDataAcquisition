"""Bound upstream work independently from the number of derived output rows."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from time import monotonic

from bioetl.domain.exceptions.internal_state import InvalidStateError

DEFAULT_SCAN_RECORDS = 50_000
DEFAULT_SCAN_SECONDS = 180.0


async def bounded_source_records[T](
    source: AsyncIterator[T],
    *,
    max_records: int = DEFAULT_SCAN_RECORDS,
    timeout_seconds: float = DEFAULT_SCAN_SECONDS,
) -> AsyncIterator[T]:
    """Fail explicitly on exhaustion; close the upstream iterator on every exit.

    Time spent processing yielded rows is excluded from the upstream I/O budget.
    One look-ahead record distinguishes natural EOF from a truncated scan.
    Cancellation propagates unchanged to the run finalization boundary.
    """
    if max_records < 1 or timeout_seconds <= 0:
        raise ValueError("scan budgets must be positive")
    consumed = 0
    remaining = timeout_seconds
    try:
        while True:
            started = monotonic()
            deadline = asyncio.timeout(max(0, remaining))
            try:
                async with deadline:
                    if remaining <= 0:
                        raise InvalidStateError(
                            "derived_scan_budget_exceeded: upstream time budget exhausted",
                            current_state="incomplete_scan",
                        )
                    record = await anext(source)
            except StopAsyncIteration:
                return
            except TimeoutError as exc:
                if not deadline.expired():
                    raise
                raise InvalidStateError(
                    "derived_scan_budget_exceeded: upstream time budget exhausted; "
                    "narrow the input selection before retrying.",
                    current_state="incomplete_scan",
                ) from exc
            remaining -= monotonic() - started
            consumed += 1
            if consumed > max_records:
                raise InvalidStateError(
                    f"derived_scan_budget_exceeded: scanned {max_records} source rows; "
                    "narrow the input selection before retrying.",
                    current_state="incomplete_scan",
                )
            yield record
    finally:
        close = getattr(source, "aclose", None)
        if close is not None:
            await close()
