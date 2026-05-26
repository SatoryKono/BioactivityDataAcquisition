# mypy: disable-error-code=attr-defined
"""Resilience, retry, and fallback helpers for ChEMBL fetch flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
)
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.chembl._fetch_resilience_error import (
    handle_fetch_error,
)
from bioetl.infrastructure.adapters.chembl._fetch_resilience_fallback import (
    _ChemblFallbackHost,
    fetch_single_record_direct,
    mark_record_as_seen,
    yield_deduplicated_filtered_records,
    yield_single_id_fallback,
)
from bioetl.infrastructure.adapters.common import is_retry_exhausted_error
from bioetl.infrastructure.adapters.common.fetch_resilience_template import (
    FilteredBatchRecoveryHost,
    fetch_batch_with_reduction,
    retry_with_split_batches,
    yield_retry_exhausted_recovery,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import (
        ChemblEntityMapper,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

CHEMBL_ADAPTER_ERRORS = (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
    httpx.HTTPError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    AttributeError,
    Exception,
)


class ChemblFetchResilienceMixin:
    """Provides retry, split-batch recovery, and single-ID fallback helpers."""

    # Host-class attributes (provided by ChemblAdapter.__init__)
    logger: LoggerPort
    _logger: LoggerPort
    provider_name: str
    _mapper: ChemblEntityMapper
    _adapter_metrics: AdapterMetricsRecorder
    http_client: UnifiedHTTPClient
    _http_client: UnifiedHTTPClient
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]

    def _handle_error(
        self,
        error: Exception,
        context: str = "fetch",
    ) -> None:
        handle_fetch_error(self, error, context)

    def _is_retry_exhausted_error(
        self,
        error: Exception,
    ) -> bool:
        """Check if exception is a retry exhausted error (direct or wrapped)."""
        return bool(is_retry_exhausted_error(error))

    async def _fetch_single_record_direct(
        self, entity_type: str, record_id: str
    ) -> BronzeRecord | None:
        """Fetch a single record using direct endpoint as fallback."""
        return await fetch_single_record_direct(
            cast(_ChemblFallbackHost, self),
            entity_type,
            record_id,
        )

    async def _retry_with_split_batches(
        self,
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
        async for record in retry_with_split_batches(
            cast(FilteredBatchRecoveryHost, self),
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

    def _mark_record_as_seen(
        self,
        record: BronzeRecord,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> bool:
        """Return True when record is new and register its dedup key."""
        return bool(
            mark_record_as_seen(
                cast(_ChemblFallbackHost, self),
                record,
                seen_ids,
                pk_field,
                pk_fields,
            )
        )

    async def _yield_deduplicated_filtered_records(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield filtered records while deduplicating by configured keys."""
        async for record in yield_deduplicated_filtered_records(
            cast(_ChemblFallbackHost, self),
            entity_type,
            id_batch,
            filter_field,
            limit,
            seen_ids,
            pk_field,
            pk_fields,
        ):
            yield record

    async def _yield_single_id_fallback(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Try direct endpoint fallback for a single failed filter ID."""
        async for record in yield_single_id_fallback(
            cast(_ChemblFallbackHost, self),
            entity_type,
            id_batch,
            filter_field,
            seen_ids,
            pk_field,
            error,
            pk_fields,
        ):
            yield record

    async def _yield_retry_exhausted_recovery(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Recover from RetryExhaustedError using shared policy orchestrator."""
        async for record in yield_retry_exhausted_recovery(
            cast(FilteredBatchRecoveryHost, self),
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

    async def _fetch_batch_with_reduction(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered batch and recover from retry-exhausted failures."""
        async for record in fetch_batch_with_reduction(
            cast(FilteredBatchRecoveryHost, self),
            entity_type,
            id_batch,
            filter_field,
            limit,
            seen_ids,
            pk_field,
            pk_fields,
        ):
            yield record


__all__ = ["CHEMBL_ADAPTER_ERRORS", "ChemblFetchResilienceMixin"]
