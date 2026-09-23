"""Bound upstream work independently from the number of derived output rows."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from time import monotonic

from bioetl.domain.exceptions.internal_state import InvalidStateError

DEFAULT_SCAN_RECORDS = 50_000
DEFAULT_SCAN_SECONDS = 180.0


def _resolve_filter_id_count(
    filter_ids: Sequence[str] | None,
    filter_id_count: int | None,
) -> int | None:
    """Normalize optional filter-id sizing inputs to a non-negative count."""
    if filter_id_count is not None:
        if filter_id_count < 0:
            raise ValueError("filter_id_count must be >= 0")
        return filter_id_count
    if filter_ids is not None:
        return len(filter_ids)
    return None


def _limit_with_lookahead(count: int, max_records: int) -> int:
    """Apply max_records cap and reserve one look-ahead slot."""
    if count < 1:
        return 1
    return min(count, max_records) + 1


def resolve_derived_upstream_limit(
    output_limit: int | None,
    *,
    multiplier: int,
    max_records: int = DEFAULT_SCAN_RECORDS,
    filter_ids: Sequence[str] | None = None,
    filter_id_count: int | None = None,
) -> int:
    """Derive an upstream source fetch/look-ahead budget for nested pipelines.

    Filtered ID lists size the upstream window directly. Output ``limit`` scales
    through ``multiplier`` (same pattern as publication_term) and is capped by
    ``max_records``. Unlimited output keeps the full scan ceiling. The returned
    value includes the look-ahead slot used by :func:`bounded_source_records`.
    """
    if multiplier < 1:
        raise ValueError("multiplier must be >= 1")
    if max_records < 1:
        raise ValueError("max_records must be >= 1")
    count = _resolve_filter_id_count(filter_ids, filter_id_count)
    if count is not None:
        return _limit_with_lookahead(count, max_records)
    if output_limit is None:
        return max_records + 1
    if output_limit < 0:
        raise ValueError("output_limit must be >= 0")
    return _limit_with_lookahead(output_limit * multiplier, max_records)


async def bounded_source_records[T](
    source: AsyncIterator[T],
    *,
    max_records: int = DEFAULT_SCAN_RECORDS,
    timeout_seconds: float = DEFAULT_SCAN_SECONDS,
) -> AsyncGenerator[T, None]:
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
