# mypy: disable-error-code=attr-defined
"""Resilience, retry, and fallback helpers for ChEMBL fetch flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.chembl._fetch_resilience_error import (
    CHEMBL_ADAPTER_ERRORS as _CHEMBL_ADAPTER_ERRORS,
)
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
    bind_host_async_iterator,
    fetch_batch_with_reduction,
    retry_with_split_batches,
    yield_retry_exhausted_recovery,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort
    from bioetl.domain.types import HealthStatus
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import (
        ChemblEntityMapper,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

CHEMBL_ADAPTER_ERRORS = _CHEMBL_ADAPTER_ERRORS


class ChemblFetchResilienceMixin:
    """Provides retry, split-batch recovery, and single-ID fallback helpers."""

    CHEMBL_ADAPTER_ERRORS = _CHEMBL_ADAPTER_ERRORS

    # Host-class attributes (provided by ChemblAdapter.__init__)
    logger: LoggerPort
    _logger: LoggerPort
    provider_name: str
    _mapper: ChemblEntityMapper
    _adapter_metrics: AdapterMetricsRecorder
    http_client: UnifiedHTTPClient
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]

    if TYPE_CHECKING:

        def _get_health_status(self) -> HealthStatus: ...

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

    # Keep legacy Chembl method names bound to the shared recovery template.
    _retry_with_split_batches = retry_with_split_batches
    _yield_deduplicated_filtered_records = bind_host_async_iterator(
        yield_deduplicated_filtered_records
    )
    _yield_single_id_fallback = bind_host_async_iterator(yield_single_id_fallback)
    _yield_retry_exhausted_recovery = yield_retry_exhausted_recovery
    _fetch_batch_with_reduction = fetch_batch_with_reduction


__all__ = ["CHEMBL_ADAPTER_ERRORS", "ChemblFetchResilienceMixin"]
