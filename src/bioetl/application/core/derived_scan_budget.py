"""Bound upstream work independently from the number of derived output rows."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Sequence

from bioetl.domain.exceptions.internal_state import InvalidStateError

DEFAULT_SCAN_RECORDS = 50_000
DEFAULT_SCAN_SECONDS = 180.0


def look_ahead_budget(count: int, max_records: int) -> int:
    if count < 0:
        raise ValueError("count must be >= 0")
    return 1 if count < 1 else min(count, max_records) + 1


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
    ``max_records``. Unlimited output keeps the full scan ceiling plus the
    look-ahead slot used by :func:`bounded_source_records`. A limited window
    that already sits on ``max_records`` does not add that slot: the extra row
    would be reported as an incomplete scan even though the caller asked only
    for a bounded sample.
    """
    if multiplier < 1:
        raise ValueError("multiplier must be >= 1")
    if max_records < 1:
        raise ValueError("max_records must be >= 1")
    count: int | None = filter_id_count
    if count is None and filter_ids is not None:
        count = len(filter_ids)
    if count is not None:
        return look_ahead_budget(count, max_records)
    if output_limit is None:
        return max_records + 1
    if output_limit < 1:
        return look_ahead_budget(output_limit, max_records)
    scaled = output_limit * multiplier
    if scaled >= max_records:
        return max_records
    return scaled + 1


def iter_derived_source[T](
    source: AsyncIterator[T],
    *,
    output_limit: int | None,
    scan_limit: int,
) -> AsyncGenerator[T, None]:
    """Bound one derived upstream scan.

    An explicit output limit stops when ``scan_limit`` source rows have been
    seen and returns those rows. An unlimited scan still fails once the default
    record ceiling is passed, so a full extract cannot certify a truncated
    source as complete.
    """
    if output_limit is None:
        return bounded_source_records(source)
    return bounded_source_records(
        source,
        max_records=scan_limit,
        stop_on_exhaustion=True,
    )


async def bounded_source_records[T](
    source: AsyncIterator[T],
    *,
    max_records: int = DEFAULT_SCAN_RECORDS,
    timeout_seconds: float = DEFAULT_SCAN_SECONDS,
    stop_on_exhaustion: bool = False,
) -> AsyncGenerator[T, None]:
    """Fail explicitly on record-budget exhaustion; close the iterator on every exit.

    ``stop_on_exhaustion`` ends the sample instead of raising when the record
    ceiling is passed. A stalled upstream read still raises.

    ``timeout_seconds`` is hang detection for a single upstream ``anext``, not a
    cumulative I/O cap. One in-flight ``anext`` may use a second hang window
    without being cancelled, so a slow ChEMBL page can finish. A second hang
    on the same wait still fails closed. A progressing paginated scan may run
    until ``max_records`` or natural EOF. Time spent processing yielded rows is
    excluded: the next wait starts after ``yield``. Cancellation propagates
    unchanged to the run finalization boundary.
    """
    if max_records < 1 or timeout_seconds <= 0:
        raise ValueError("scan budgets must be positive")
    consumed = 0
    hang_retries = 0
    pending: asyncio.Task[T] | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(source))  # type: ignore[arg-type]
            try:
                record = await asyncio.wait_for(
                    asyncio.shield(pending),
                    timeout=timeout_seconds,
                )
            except StopAsyncIteration:
                pending = None
                return
            except TimeoutError as exc:
                if pending is not None and pending.done():
                    pending = None
                    raise
                if hang_retries == 0:
                    hang_retries += 1
                    continue
                pending.cancel()
                try:
                    await pending
                except (asyncio.CancelledError, StopAsyncIteration, TimeoutError):
                    pass
                pending = None
                raise InvalidStateError(
                    "derived_scan_budget_exceeded: upstream time budget exhausted; "
                    "narrow the input selection before retrying.",
                    current_state="incomplete_scan",
                ) from exc
            pending = None
            consumed += 1
            hang_retries = 0
            if consumed > max_records:
                if stop_on_exhaustion:
                    return
                raise InvalidStateError(
                    f"derived_scan_budget_exceeded: scanned {max_records} source rows; "
                    "narrow the input selection before retrying.",
                    current_state="incomplete_scan",
                )
            yield record
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            try:
                await pending
            except (asyncio.CancelledError, StopAsyncIteration, TimeoutError):
                pass
        close = getattr(source, "aclose", None)
        if close is not None:
            await close()
