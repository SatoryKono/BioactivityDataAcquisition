"""ChEMBL data source adapter implementing DataSourcePort.

Uses chembl_webresource_client library. Error handling per RULES.md §3.1.
Health-aware fetching: HEALTHY=full batch, DEGRADED=batch/2, UNHEALTHY=fail fast.
DTO support via fetch_as_models() returning typed Pydantic models.
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

from pydantic import BaseModel

from bioetl.domain.entities.chembl import (
    ActivityRecord,
    AssayRecord,
    CellLineRecord,
    ChemblPublicationRecord,
    MoleculeRecord,
    ProteinClassRecord,
    TargetComponentRecord,
    TargetRecord,
)
from bioetl.domain.exceptions import (
    CriticalError,
    ExternalServiceError,
    RetryExhaustedError,
)
from bioetl.domain.ports import NoOpMetrics
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.chembl.entity_mapper import (
    CHEMBL_API_BASE,
    CHEMBL_STATUS_URL,
    ChemblEntityMapper,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# Mapping from entity_type to DTO model class
CHEMBL_DTO_MODELS: dict[str, type[BaseModel]] = {
    "activity": ActivityRecord,
    "assay": AssayRecord,
    "molecule": MoleculeRecord,
    "compound": MoleculeRecord,  # Alias for molecule
    "target": TargetRecord,
    "target_component": TargetComponentRecord,
    "document": ChemblPublicationRecord,
    "cell_line": CellLineRecord,
    "protein_class": ProteinClassRecord,
}


@dataclass
class ChemblAdapter(BaseHttpAdapter):
    """ChEMBL data source adapter implementing DataSourcePort.

    Configuration: Load from configs/sources/chembl.yaml via AdapterConfig.
    Health-aware: HEALTHY=full batch, DEGRADED=batch/2, UNHEALTHY=CriticalError.
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    adapter_config: AdapterConfig | None = None
    thread_pool: ThreadPoolExecutor | None = None
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="chembl")
    """Provider identifier (required by DataSourcePort)."""

    # Resolved configuration values (computed in __post_init__)
    _page_size: int = field(init=False, default=1000)
    _filter_batch_size: int = field(init=False, default=20)

    # Entity mapper for URL and key resolution
    _mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)

    # API request collector for metadata enrichment
    _request_collector: APIRequestCollector = field(
        init=False, default_factory=APIRequestCollector
    )

    def __post_init__(self) -> None:
        """Initialize adapter with config values and metrics."""
        # Initialize error handler from base class
        self._error_handler = ErrorService(self.logger)
        # Resolve configuration: use provided config or domain defaults
        config = (
            self.adapter_config if self.adapter_config is not None else AdapterConfig()
        )
        self._page_size = config.page_size
        self._filter_batch_size = config.batch_size

        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    @property
    def effective_batch_size(self) -> int:
        """Get configured page size for API requests."""
        return self._page_size

    def _get_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state."""
        return assess_health_from_circuit_breaker(self.http_client.circuit_breaker)

    def _get_effective_batch_size(self) -> int:
        """Get batch size adjusted for health: full if HEALTHY, half if DEGRADED."""
        health_status = self._get_health_status()
        failure_count = self.http_client.circuit_breaker.get_failure_count()

        if health_status == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"ChEMBL adapter is UNHEALTHY after {failure_count} "
                f"consecutive errors (circuit breaker)"
            )
        if health_status == HealthStatus.DEGRADED:
            reduced = max(100, self._page_size // 2)  # Minimum 100
            self.logger.warning(
                "chembl_degraded_mode",
                provider="chembl",
                original_batch_size=self._page_size,
                effective_batch_size=reduced,
                consecutive_errors=failure_count,
            )
            return reduced
        return self._page_size

    def _build_params(self, offset: int) -> dict[str, Any]:
        """Build API request parameters with health-aware batch size."""
        return {
            "limit": self._get_effective_batch_size(),
            "offset": offset,
            "format": "json",
        }

    def _process_response(
        self, response: Response, entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Process API response, extract records and pagination info."""
        data = response.json()
        plural_key = self._mapper.get_plural_key(entity_type)
        records = data.get(plural_key, [])
        page_meta = data.get("page_meta", {})
        has_next = page_meta.get("next") is not None
        return records, has_next

    def _batch_ids(self, ids: list[str], batch_size: int) -> Iterator[list[str]]:
        """Split IDs into batches for API requests."""
        for i in range(0, len(ids), batch_size):
            yield ids[i : i + batch_size]

    def _build_filter_in_params(self, filters: dict[str, list[str]]) -> dict[str, str]:
        """Build __in filter parameters for multi-field filtering."""
        return {
            f"{filter_field}__in": ",".join(ids)
            for filter_field, ids in filters.items()
            if ids
        }

    def _is_duplicate_record(
        self,
        record: dict[str, Any],
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate and add to seen set if not."""
        record_id = str(record.get(pk_field, ""))
        if not record_id:
            return False
        if record_id in seen_ids:
            self.logger.debug(
                "skipping_duplicate_record",
                entity_type=entity_type,
                pk_field=pk_field,
                record_id=record_id,
            )
            return True
        seen_ids.add(record_id)
        return False

    async def _fetch_page(
        self, url: str, params: dict[str, Any], entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch a single page and handle errors.

        Note: Success/failure tracking is handled by the circuit breaker
        in UnifiedHTTPClient, no duplicate tracking needed here.

        Records request metadata via APIRequestCollector for Bronze layer enrichment.
        """
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment (gracefully handle mocked responses)
            # Skip recording if response doesn't have expected attributes
            # (e.g., during testing with mocked responses or validation errors)
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            records, has_next = self._process_response(response, entity_type)
            return records, has_next
        except Exception as e:
            self._handle_error(e)

    async def _page_iterator(
        self, entity_type: str, limit: int | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield pages of records."""
        url = self._mapper.get_resource_url(entity_type)
        offset = 0
        while True:
            params = self._build_params(offset)
            # Optimize limit: if we have a global limit and it's smaller than effective batch size
            if limit is not None:
                remaining = limit - offset
                if remaining > 0:
                    params["limit"] = min(params["limit"], remaining)
                elif remaining <= 0:
                    break

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break
            yield records
            if not has_next:
                break
            # Fix: increment by actual records fetched to handle dynamic limits correctly
            offset += len(records)

    def _yield_deduplicated(
        self,
        records: list[dict[str, Any]],
        seen_ids: set[str],
        pk_field: str,
        entity_type: str,
        filter_field: str,
    ) -> Iterator[dict[str, Any]]:
        """Yield records while tracking seen IDs for deduplication."""
        for record in records:
            record_id = str(record.get(pk_field, ""))
            if record_id and record_id in seen_ids:
                self.logger.debug(
                    "skipping_duplicate_record",
                    entity_type=entity_type,
                    pk_field=pk_field,
                    record_id=record_id,
                    filter_field=filter_field,
                )
                continue
            if record_id:
                seen_ids.add(record_id)
            yield record

    async def _paginate_filter_results(
        self,
        url: str,
        id_batch: list[str],
        filter_field: str,
        entity_type: str,
        pk_field: str,
        seen_ids: set[str],
        start_offset: int,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Continue pagination after first page."""
        offset = start_offset
        while True:
            if limit and offset >= limit:
                break
            params = self._build_params(offset)
            params[f"{filter_field}__in"] = ",".join(id_batch)
            try:
                records, has_next = await self._fetch_page(url, params, entity_type)
            except Exception:
                self.logger.warning(
                    "chembl_pagination_interrupted",
                    entity_type=entity_type,
                    offset=offset,
                    records_yielded=len(seen_ids),
                )
                return
            if not records:
                break
            for record in self._yield_deduplicated(
                records, seen_ids, pk_field, entity_type, filter_field
            ):
                yield record
            if not has_next:
                break
            offset += len(records)

    async def _fetch_with_filter(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by ID batch with client-side deduplication."""
        url = self._mapper.get_resource_url(entity_type)
        seen_ids: set[str] = set()
        pk_field = self._mapper.get_primary_key_field(entity_type)

        params = self._build_params(0)
        params[f"{filter_field}__in"] = ",".join(id_batch)

        records, has_next = await self._fetch_page(url, params, entity_type)

        if not records:
            return

        for record in self._yield_deduplicated(
            records, seen_ids, pk_field, entity_type, filter_field
        ):
            yield record

        if has_next:
            async for record in self._paginate_filter_results(
                url,
                id_batch,
                filter_field,
                entity_type,
                pk_field,
                seen_ids,
                len(records),
                limit,
            ):
                yield record

    def _handle_error(self, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle errors with unified classification. Translates to domain exceptions."""
        # Build context with circuit breaker info
        failure_count = self.http_client.circuit_breaker.get_failure_count()
        health_status = self._get_health_status()

        error_context = {
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "circuit_breaker_failures": failure_count,
            "health_status": health_status.value,
        }

        # Use unified error handler
        wrapped = self._error_handler.handle_error(
            error=e,
            provider=self.provider_name,
            operation=context,
            context=error_context,
        )
        raise wrapped from e

    def _is_retry_exhausted_error(self, e: Exception) -> bool:
        """Check if exception is a retry exhausted error (direct or wrapped)."""
        if isinstance(e, RetryExhaustedError):
            return True
        # Check if it's an ExternalServiceError wrapping RetryExhaustedError
        return isinstance(e, ExternalServiceError) and isinstance(
            e.__cause__, RetryExhaustedError
        )

    def _log_single_id_failure(
        self, entity_type: str, filter_field: str, id_batch: list[str], e: Exception
    ) -> None:
        """Log single ID fetch failure for graceful degradation."""
        failed_id = id_batch[0] if id_batch else "unknown"
        self.logger.error(
            "single_id_fetch_failed",
            provider=self.provider_name,
            entity_type=entity_type,
            filter_field=filter_field,
            failed_id=failed_id,
            error=str(e),
            error_class=type(e).__name__,
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
    ) -> AsyncIterator[dict[str, Any]]:
        """Split failed batch in half and retry each part recursively."""
        mid = len(id_batch) // 2
        first_half, second_half = id_batch[:mid], id_batch[mid:]

        self.logger.warning(
            "batch_reduction_retry",
            provider=self.provider_name,
            entity_type=entity_type,
            original_batch_size=len(id_batch),
            first_half_size=len(first_half),
            second_half_size=len(second_half),
            filter_field=filter_field,
            error=str(error),
        )

        async for record in self._fetch_batch_with_reduction(
            entity_type, first_half, filter_field, limit, seen_ids, pk_field
        ):
            yield record
        async for record in self._fetch_batch_with_reduction(
            entity_type, second_half, filter_field, limit, seen_ids, pk_field
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
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch a batch of IDs with automatic batch size reduction on failures."""
        try:
            async for record in self._fetch_with_filter(
                entity_type, id_batch, filter_field, limit
            ):
                record_id = str(record.get(pk_field, ""))
                if not record_id or record_id not in seen_ids:
                    if record_id:
                        seen_ids.add(record_id)
                    yield record
        except (RetryExhaustedError, ExternalServiceError) as e:
            if not self._is_retry_exhausted_error(e):
                raise
            if len(id_batch) > 1:
                async for record in self._retry_with_split_batches(
                    entity_type, id_batch, filter_field, limit, seen_ids, pk_field, e
                ):
                    yield record
            else:
                self._log_single_id_failure(entity_type, filter_field, id_batch, e)

    async def _fetch_filtered(
        self,
        entity_type: str,
        limit: int | None,
        filter_ids: list[str],
        filter_field: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform filtered fetch using ID batches with client-side deduplication.

        Uses batch reduction strategy: on failures, splits batch in half
        and retries each part recursively until success or single-ID failure.
        """
        total_fetched = 0
        seen_ids: set[str] = set()
        pk_field = self._mapper.get_primary_key_field(entity_type)

        for id_batch in self._batch_ids(filter_ids, batch_size=self._filter_batch_size):
            async for record in self._fetch_batch_with_reduction(
                entity_type, id_batch, filter_field, limit, seen_ids, pk_field
            ):
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def _fetch_standard(
        self,
        entity_type: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform standard paginated fetch with client-side deduplication.

        ChEMBL API pagination can return duplicate records across pages
        due to unstable sorting or data changes between requests.
        This method deduplicates records by primary key field.
        """
        total_fetched = 0
        seen_ids: set[str] = set()
        pk_field = self._mapper.get_primary_key_field(entity_type)

        async for records in self._page_iterator(entity_type, limit):
            for record in records:
                record_id = str(record.get(pk_field, ""))
                if record_id and record_id in seen_ids:
                    self.logger.debug(
                        "skipping_duplicate_record",
                        entity_type=entity_type,
                        pk_field=pk_field,
                        record_id=record_id,
                    )
                    continue
                if record_id:
                    seen_ids.add(record_id)
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity to fetch (activity, assay, compound, etc.)
            limit: Maximum number of records to fetch
            query: Unused for ChEMBL
            filter_ids: List of IDs to filter by (for deterministic batching)
            filter_field: Field name to filter on

        Yields:
            Dictionary records from ChEMBL API

        """
        if filter_ids and filter_field:
            async for record in self._fetch_filtered(
                entity_type, limit, filter_ids, filter_field
            ):
                yield record
        else:
            async for record in self._fetch_standard(entity_type, limit):
                yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL with ID filtering.

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Type of entity to fetch
            filter_ids: Sorted list of IDs to filter by (for deterministic batching)
            filter_field: Field name to filter on
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching the filter criteria

        """
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL with multiple filter fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Makes requests with multiple __in parameters, e.g.:
        ?molecule_chembl_id__in=CHEMBL25,CHEMBL26&document_chembl_id__in=CHEMBL1123

        ChEMBL API returns records matching ALL filter conditions (AND logic).

        Args:
            entity_type: Type of entity to fetch
            filters: Mapping from filter_field to list of IDs
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching ALL filter criteria

        """
        filter_params = self._build_filter_in_params(filters)
        if not filter_params:
            return

        url = self._mapper.get_resource_url(entity_type)
        pk_field = self._mapper.get_primary_key_field(entity_type)
        offset = 0
        total_fetched = 0
        seen_ids: set[str] = set()

        while True:
            params = self._build_params(offset)
            params.update(filter_params)

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break

            for record in records:
                if self._is_duplicate_record(record, pk_field, seen_ids, entity_type):
                    continue
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

            if not has_next:
                break
            offset += len(records)

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with fallback (ChEMBL IDs always resolvable, fallback ignored)."""
        _ = fallback_mapping  # Unused - ChEMBL IDs are always resolvable
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record

    async def fetch_as_models(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        *,
        validate: bool = True,
    ) -> AsyncIterator[BaseModel]:
        """Fetch records from ChEMBL as typed DTO models.

        Returns Pydantic DTO models instead of raw dicts for type safety.
        Uses domain DTOs with extra='forbid' to detect API changes.

        Args:
            entity_type: Type of entity (activity, assay, molecule, target, etc.)
            limit: Maximum number of records to fetch
            query: Unused for ChEMBL
            filter_ids: List of IDs to filter by
            filter_field: Field name to filter on
            validate: If True, validate with model_validate (strict).
                     If False, use model_construct (skip validation, faster).

        Yields:
            Typed DTO models (ActivityRecord, AssayRecord, etc.)

        Raises:
            ValueError: If entity_type is not supported for DTO conversion
            ValidationError: If validate=True and API response has unexpected fields

        Example:
            >>> async for activity in adapter.fetch_as_models("activity", limit=100):
            ...     logger.debug("activity_fetched", activity_id=activity.activity_id, pchembl=activity.pchembl_value)

        """
        model_class = CHEMBL_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(
                f"No DTO model for entity_type '{entity_type}'. "
                f"Supported: {', '.join(CHEMBL_DTO_MODELS.keys())}"
            )

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            if validate:
                # Strict validation - will raise on unknown fields
                yield model_class.model_validate(record)
            else:
                # Fast path - skip validation for trusted data
                yield model_class.model_construct(**record)

    async def _probe_health(self) -> HealthStatus:
        """Perform ChEMBL-specific health probe.

        Overrides BaseHttpAdapter._probe_health() to use ChEMBL status endpoint.
        Uses circuit breaker state for health tracking.

        Returns:
            HealthStatus based on status endpoint response and circuit breaker state.

        Raises:
            Exception: On request failure (base class handles via _fallback_health_status).

        """
        try:
            with self._adapter_metrics.measure_request("/status"):
                response = await self.http_client.get_once(CHEMBL_STATUS_URL)
            return self._handle_health_response(response)
        except Exception as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise  # Let base class handle via _fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Return health status based on circuit breaker state.

        Returns:
            HealthStatus based on circuit breaker failure count.

        """
        return self._get_health_status()

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for ChEMBL.

        Returns:
            ChEMBL status endpoint path.

        """
        return "/chembl/api/data/status.json"

    def _handle_health_response(self, response: Response) -> HealthStatus:
        """Process health check response.

        Args:
            response: HTTP response from status endpoint

        Returns:
            HealthStatus based on response and API status.
        """
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "UP":
                return HealthStatus.HEALTHY
            else:
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="status_not_up",
                    api_status=data.get("status"),
                )
                return HealthStatus.DEGRADED
        else:
            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )
            return HealthStatus.DEGRADED

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics from circuit breaker for monitoring.

        Returns:
            Dictionary with circuit breaker stats and health status.

        """
        return {
            "circuit_breaker_failures": self.http_client.circuit_breaker.get_failure_count(),
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "health_status": self._get_health_status().value,
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (e.g., after successful recovery)."""
        self.http_client.circuit_breaker.reset()
        self.logger.info("chembl_circuit_breaker_reset", provider="chembl")

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities."""
        url = self._mapper.get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}
        with self._adapter_metrics.measure_request(f"/{entity_type}/count"):
            response = await self.http_client.get(url, params=params)
        data = response.json()
        page_meta = data.get("page_meta", {})
        total_count: int = page_meta.get("total_count", 0)
        return total_count

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector."""
        metadata = self._request_collector.to_source_metadata(
            source_type="api", url=CHEMBL_API_BASE, api_version=api_version
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return self._request_collector.request_count
