# mypy: disable-error-code=attr-defined
"""Internal fallback and dedup helpers for ChEMBL fetch resilience."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    async_iter_deduplicated_records,
    is_new_record,
)
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_ADAPTER_FETCH_RESILIENCE_ERRORS,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import (
        ChemblEntityMapper,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.common.fetch_resilience_template import (
        FilteredBatchRecoveryHost,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

    class _ChemblFallbackHost(FilteredBatchRecoveryHost, Protocol):
        """Type-only host contract required by ChEMBL fallback helpers."""

        _mapper: ChemblEntityMapper
        _adapter_metrics: AdapterMetricsRecorder
        _http_client: UnifiedHTTPClient
        _request_collector: APIRequestCollector
        _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]

        def _fetch_with_filter(
            self,
            entity_type: str,
            id_batch: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[BronzeRecord]: ...
else:
    _ChemblFallbackHost = object

CHEMBL_FALLBACK_ERRORS = COMMON_ADAPTER_FETCH_RESILIENCE_ERRORS


def _log_single_id_failure(
    logger: LoggerPort,
    provider_name: str,
    entity_type: str,
    filter_field: str,
    id_batch: list[str],
    error: Exception,
) -> None:
    """Log single ID fetch failure for graceful degradation."""
    failed_id = id_batch[0] if id_batch else "unknown"
    logger.error(
        "single_id_fetch_failed",
        provider=provider_name,
        entity_type=entity_type,
        filter_field=filter_field,
        failed_id=failed_id,
        error=str(error),
        error_class=type(error).__name__,
    )


async def fetch_single_record_direct(
    host: _ChemblFallbackHost,
    entity_type: str,
    record_id: str,
) -> BronzeRecord | None:
    """Fetch a single record using direct endpoint as fallback."""
    direct_url = host._mapper.get_direct_record_url(entity_type, record_id)
    params = {"format": "json"}

    try:
        start_time = time.perf_counter()
        with host._adapter_metrics.measure_request(f"/{entity_type}/direct_record"):
            response = await host._http_client.get(direct_url, params=params)
        duration_ms = (time.perf_counter() - start_time) * 1000

        with contextlib.suppress(Exception):
            host._request_collector.record_from_response(response, duration_ms)

        data = response.json()
        if isinstance(data, dict) and not data.get("page_meta"):
            host._logger.info(
                "direct_endpoint_fallback_success",
                entity_type=entity_type,
                record_id=record_id,
            )
            return data
        return None
    except CHEMBL_FALLBACK_ERRORS as error:
        host._logger.warning(
            "direct_endpoint_fallback_failed",
            entity_type=entity_type,
            record_id=record_id,
            error=str(error),
            error_class=type(error).__name__,
        )
        return None


def mark_record_as_seen(
    host: _ChemblFallbackHost,
    record: BronzeRecord,
    seen_ids: set[str],
    pk_field: str,
    pk_fields: tuple[str, ...] | None = None,
) -> bool:
    """Return True when record is new and register its dedup key."""
    return is_new_record(
        record=record,
        seen_keys=seen_ids,
        primary_field=pk_field,
        composite_fields=pk_fields,
        composite_key_builder=host._compute_composite_key,
    )


async def yield_deduplicated_filtered_records(
    host: _ChemblFallbackHost,
    entity_type: str,
    id_batch: list[str],
    filter_field: str,
    limit: int | None,
    seen_ids: set[str],
    pk_field: str,
    pk_fields: tuple[str, ...] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Yield filtered records while deduplicating by configured keys."""
    async for record in async_iter_deduplicated_records(
        host._fetch_with_filter(
            entity_type,
            id_batch,
            filter_field,
            limit,
        ),
        seen_keys=seen_ids,
        primary_field=pk_field,
        composite_fields=pk_fields,
        composite_key_builder=host._compute_composite_key,
    ):
        yield record


async def yield_single_id_fallback(
    host: _ChemblFallbackHost,
    entity_type: str,
    id_batch: list[str],
    filter_field: str,
    seen_ids: set[str],
    pk_field: str,
    error: Exception,
    pk_fields: tuple[str, ...] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Try direct endpoint fallback for a single failed filter ID."""
    single_id = id_batch[0]
    direct_record = await fetch_single_record_direct(host, entity_type, single_id)
    if direct_record is None:
        _log_single_id_failure(
            host._logger,
            host.provider_name,
            entity_type,
            filter_field,
            id_batch,
            error,
        )
        return

    if mark_record_as_seen(host, direct_record, seen_ids, pk_field, pk_fields):
        yield direct_record
