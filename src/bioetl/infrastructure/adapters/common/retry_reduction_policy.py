"""Shared retry-exhausted recovery policy for adapter batch fetch flows."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

from bioetl.domain.types import BronzeRecord

__all__ = ["run_retry_exhausted_recovery_policy"]


async def run_retry_exhausted_recovery_policy(
    *,
    id_batch: list[str],
    retry_error: Exception,
    on_split: Callable[[list[str], list[str], Exception], None] | None,
    fetch_reduced_batch: Callable[[list[str]], AsyncIterator[BronzeRecord]],
    fetch_single_fallback: Callable[[str, Exception], AsyncIterator[BronzeRecord]],
) -> AsyncIterator[BronzeRecord]:
    """Recover from retry-exhausted failures with split-or-single strategy.

    Strategy:
    - Multi-ID batches are split into halves and each half is delegated to
      ``fetch_reduced_batch``.
    - Single-ID batches are delegated to ``fetch_single_fallback``.
    """
    if not id_batch:
        return

    if len(id_batch) > 1:
        mid = len(id_batch) // 2
        first_half = id_batch[:mid]
        second_half = id_batch[mid:]
        if on_split is not None:
            on_split(first_half, second_half, retry_error)

        async for record in fetch_reduced_batch(first_half):
            yield record
        async for record in fetch_reduced_batch(second_half):
            yield record
        return

    async for record in fetch_single_fallback(id_batch[0], retry_error):
        yield record
