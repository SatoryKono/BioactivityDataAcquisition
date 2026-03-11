# mypy: disable-error-code=attr-defined
"""Resilience, retry, and fallback helpers for ChEMBL fetch flows."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
)
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common import (
    is_retry_exhausted_error,
    run_retry_exhausted_recovery_policy,
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


def _log_batch_reduction_retry(
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


class ChemblFetchResilienceMixin:
    """Provides retry, split-batch recovery, and single-ID fallback helpers."""

    # Host-class attributes (provided by ChemblAdapter.__init__)
    logger: LoggerPort
    provider_name: str
    _mapper: ChemblEntityMapper
    _adapter_metrics: AdapterMetricsRecorder
    http_client: UnifiedHTTPClient
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]

    def _handle_error(
        self,
        error: Exception,
        context: str = "fetch",
    ) -> None:
        """Handle errors with unified classification."""
        failure_count = self._http_client.circuit_breaker.get_failure_count()
        health_status = self._get_health_status()

        error_context = {
            "circuit_breaker_state": self._http_client.circuit_breaker.get_state().value,
            "circuit_breaker_failures": failure_count,
            "health_status": health_status.value,
        }
        wrapped = self._error_handler.handle_error(
            error=error,
            provider=self.provider_name,
            operation=context,
            context=error_context,
        )
        raise wrapped from error

    def _is_retry_exhausted_error(
        self,
        error: Exception,
    ) -> bool:
        """Check if exception is a retry exhausted error (direct or wrapped)."""
        return is_retry_exhausted_error(error)

    async def _fetch_single_record_direct(
        self, entity_type: str, record_id: str
    ) -> BronzeRecord | None:
        """Fetch a single record using direct endpoint as fallback."""
        direct_url = self._mapper.get_direct_record_url(entity_type, record_id)
        params = {"format": "json"}

        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}/{record_id}"):
                response = await self._http_client.get(direct_url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            data = response.json()
            if isinstance(data, dict) and not data.get("page_meta"):
                self._logger.info(
                    "direct_endpoint_fallback_success",
                    entity_type=entity_type,
                    record_id=record_id,
                )
                return data
            return None
        except CHEMBL_ADAPTER_ERRORS as error:
            self._logger.warning(
                "direct_endpoint_fallback_failed",
                entity_type=entity_type,
                record_id=record_id,
                error=str(error),
                error_class=type(error).__name__,
            )
            return None

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

        async def _fetch_reduced_batch(batch: list[str]) -> AsyncIterator[BronzeRecord]:
            async for record in self._fetch_batch_with_reduction(
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
            async for record in self._yield_single_id_fallback(
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
            on_split=lambda first_half, second_half, retry_error: (
                _log_batch_reduction_retry(
                    self._logger,
                    self.provider_name,
                    entity_type=entity_type,
                    filter_field=filter_field,
                    id_batch=id_batch,
                    first_half=first_half,
                    second_half=second_half,
                    error=retry_error,
                )
            ),
            fetch_reduced_batch=_fetch_reduced_batch,
            fetch_single_fallback=_fetch_single_fallback,
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
        use_composite = pk_fields is not None and len(pk_fields) > 1
        if use_composite:
            assert pk_fields is not None
            composite_key = self._compute_composite_key(record, pk_fields)
            if not composite_key or composite_key in seen_ids:
                return False
            seen_ids.add(composite_key)
            return True

        record_id = str(record.get(pk_field, ""))
        if not record_id or record_id in seen_ids:
            return False
        seen_ids.add(record_id)
        return True

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
        async for record in self._fetch_with_filter(
            entity_type, id_batch, filter_field, limit
        ):
            if self._mark_record_as_seen(record, seen_ids, pk_field, pk_fields):
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
        single_id = id_batch[0]
        direct_record = await self._fetch_single_record_direct(entity_type, single_id)
        if direct_record is None:
            _log_single_id_failure(
                self._logger,
                self.provider_name,
                entity_type,
                filter_field,
                id_batch,
                error,
            )
            return

        if self._mark_record_as_seen(direct_record, seen_ids, pk_field, pk_fields):
            yield direct_record

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
        async for record in self._retry_with_split_batches(
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
        retry_error: Exception | None = None
        try:
            async for record in self._yield_deduplicated_filtered_records(
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
            if not self._is_retry_exhausted_error(error):
                raise
            retry_error = error

        assert retry_error is not None
        async for record in self._yield_retry_exhausted_recovery(
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


__all__ = ["CHEMBL_ADAPTER_ERRORS", "ChemblFetchResilienceMixin"]
