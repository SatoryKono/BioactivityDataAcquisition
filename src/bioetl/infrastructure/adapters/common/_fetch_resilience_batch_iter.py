"""Batch iteration helpers for filtered-fetch resilience templates."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common._fetch_resilience_host import (
    FilteredBatchRecoveryHost,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
else:
    AsyncIterator = object

__all__ = [
    "bind_host_async_iterator",
    "iter_deduplicated_filtered_id_batches",
]


def bind_host_async_iterator(
    host_fn: Callable[..., AsyncIterator[BronzeRecord]],
) -> Callable[..., AsyncIterator[BronzeRecord]]:
    """Bind a host-first async iterator helper as an instance method."""

    async def bound(
        self: FilteredBatchRecoveryHost,
        /,
        *args: object,
        **kwargs: object,
    ) -> AsyncIterator[BronzeRecord]:
        async for record in host_fn(self, *args, **kwargs):
            yield record

    return bound


async def iter_deduplicated_filtered_id_batches(
    host: FilteredBatchRecoveryHost,
    *,
    entity_type: str,
    limit: int | None,
    filter_ids: list[str],
    filter_field: str,
    batch_size: int,
) -> AsyncIterator[BronzeRecord]:
    """Yield deduplicated records across filtered ID batches."""
    total_fetched = 0
    seen_ids: set[str] = set()
    pk_field = host._get_api_pk_field(entity_type)
    pk_fields = host._get_api_dedup_fields(entity_type)
    for id_batch in host._batch_ids(filter_ids, batch_size=batch_size):
        async for record in host._fetch_batch_with_reduction(
            entity_type,
            id_batch,
            filter_field,
            limit,
            seen_ids,
            pk_field,
            pk_fields,
        ):
            yield record
            total_fetched += 1
            if limit and total_fetched >= limit:
                return
