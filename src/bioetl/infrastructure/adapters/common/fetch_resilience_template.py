"""Shared resilience template for adapter filtered-fetch recovery flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.exceptions import ExternalServiceError, RetryExhaustedError
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.retry_reduction_policy import (
    run_retry_exhausted_recovery_policy,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort

else:
    AsyncIterator = object
    LoggerPort = object


class FilteredBatchRecoveryHost(Protocol):
    """Host contract for shared filtered batch recovery helpers."""

    _logger: LoggerPort
    provider_name: str

    def _is_retry_exhausted_error(self, error: Exception) -> bool: ...

    def _fetch_batch_with_reduction(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _yield_single_id_fallback(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _batch_ids(
        self, filter_ids: list[str], *, batch_size: int
    ) -> object: ...

    def _get_api_pk_field(self, entity_type: str) -> str: ...

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]: ...

    def _yield_deduplicated_filtered_records(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...


__all__ = [
    "FilteredBatchRecoveryHost",
    "bind_host_async_iterator",
    "fetch_batch_with_reduction",
    "iter_deduplicated_filtered_id_batches",
    "log_batch_reduction_retry",
    "retry_with_split_batches",
    "yield_retry_exhausted_recovery",
]


def log_batch_reduction_retry(
    logger: LoggerPort,
    provider_name: str,
    *,
    entity_type: str,
    filter_field: str,
    id_batch: list[str],
    first_half: list[str],
    second_half: list[str],
    error: Exception,
) -> None:
    """Log split-batch retry decision for retry-exhausted failures."""
    logger.warning(
        "batch_reduction_retry",
        provider=provider_name,
        entity_type=entity_type,
        original_batch_size=len(id_batch),
        first_half_size=len(first_half),
        second_half_size=len(second_half),
        filter_field=filter_field,
        error=str(error),
    )


async def retry_with_split_batches(
    host: FilteredBatchRecoveryHost,
    entity_type: str,
    id_batch: list[str],
    filter_field: str,
    limit: int | None,
    seen_ids: set[str],
    pk_field: str,
    error: Exception,
    pk_fields: tuple[str, ...] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Recover retry-exhausted batch via shared split-or-single policy."""

    async def _fetch_reduced_batch(batch: list[str]) -> AsyncIterator[BronzeRecord]:
        async for record in host._fetch_batch_with_reduction(
            entity_type,
            batch,
            filter_field,
            limit,
            seen_ids,
            pk_field,
            pk_fields,
        ):
            yield record

    async def _fetch_single_fallback(
        single_id: str, retry_error: Exception
    ) -> AsyncIterator[BronzeRecord]:
        async for record in host._yield_single_id_fallback(
            entity_type,
            [single_id],
            filter_field,
            seen_ids,
            pk_field,
            retry_error,
            pk_fields,
        ):
            yield record

    async for record in run_retry_exhausted_recovery_policy(
        id_batch=id_batch,
        retry_error=error,
        on_split=lambda first_half, second_half, retry_error: log_batch_reduction_retry(
            host._logger,
            host.provider_name,
            entity_type=entity_type,
            filter_field=filter_field,
            id_batch=id_batch,
            first_half=first_half,
            second_half=second_half,
            error=retry_error,
        ),
        fetch_reduced_batch=_fetch_reduced_batch,
        fetch_single_fallback=_fetch_single_fallback,
    ):
        yield record


async def yield_retry_exhausted_recovery(
    host: FilteredBatchRecoveryHost,
    entity_type: str,
    id_batch: list[str],
    filter_field: str,
    limit: int | None,
    seen_ids: set[str],
    pk_field: str,
    error: Exception,
    pk_fields: tuple[str, ...] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Recover from RetryExhaustedError using the shared recovery template."""
    async for record in retry_with_split_batches(
        host,
        entity_type,
        id_batch,
        filter_field,
        limit,
        seen_ids,
        pk_field,
        error,
        pk_fields,
    ):
        yield record


async def fetch_batch_with_reduction(
    host: FilteredBatchRecoveryHost,
    entity_type: str,
    id_batch: list[str],
    filter_field: str,
    limit: int | None,
    seen_ids: set[str],
    pk_field: str,
    pk_fields: tuple[str, ...] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Fetch filtered batch and recover from retry-exhausted failures."""
    retry_error: Exception | None = None
    try:
        async for record in host._yield_deduplicated_filtered_records(
            entity_type,
            id_batch,
            filter_field,
            limit,
            seen_ids,
            pk_field,
            pk_fields,
        ):
            yield record
        return
    except (RetryExhaustedError, ExternalServiceError) as error:
        if not host._is_retry_exhausted_error(error):
            raise
        retry_error = error

    assert retry_error is not None
    async for record in yield_retry_exhausted_recovery(
        host,
        entity_type,
        id_batch,
        filter_field,
        limit,
        seen_ids,
        pk_field,
        retry_error,
        pk_fields,
    ):
        yield record


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
