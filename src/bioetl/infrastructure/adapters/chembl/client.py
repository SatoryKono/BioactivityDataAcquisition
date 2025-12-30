"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.

Uses chembl_webresource_client library for API access.

Error Handling (RULES.md §4.1):
Uses unified AdapterErrorHandler for consistent error classification:
- CRITICAL errors (401, 403): Fail immediately with AuthFailureError
- RECOVERABLE errors (429, 5xx): Retry with exponential backoff
- DATA_QUALITY errors: Log and skip record

Health-Aware Fetching:
- Uses circuit breaker state for health-aware batch sizing
- HEALTHY: Normal batch_size
- DEGRADED: batch_size ÷ 2 (per RULES.md §3.5)
- UNHEALTHY: Fail fast with clear error
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

from bioetl.domain.exceptions import CriticalError
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.chembl.entity_mapper import (
    CHEMBL_STATUS_URL,
    ChemblEntityMapper,
)
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass
class ChemblAdapter(BaseHttpAdapter):
    """ChEMBL data source adapter.

    Implements DataSourcePort and FilterableDataSourcePort for fetching
    data from ChEMBL database with optional server-side filtering.

    Configuration is loaded from configs/sources/chembl.yaml and passed
    via AdapterConfig. This ensures YAML is the single source of truth
    (RULES.md §12.1.2).

    Args:
        http_client: UnifiedHTTPClient instance
        logger: LoggerPort instance for structured logging
        adapter_config: Configuration from YAML (preferred). Contains batch_size,
            page_size, timeout_sec, max_retries. If not provided, falls back to
            batch_size/filter_batch_size parameters for backward compatibility.
        batch_size: DEPRECATED. Use adapter_config.page_size instead.
            Number of records per API request. Fallback if adapter_config not provided.
        filter_batch_size: DEPRECATED. Use adapter_config.batch_size instead.
            Number of IDs per filtered API request. Fallback if adapter_config not provided.
        thread_pool: ThreadPoolExecutor for sync operations
        metrics: MetricsPort instance for observability

    Health-Aware Behavior (uses circuit breaker state):
        - HEALTHY: Uses configured batch_size
        - DEGRADED: Uses batch_size ÷ 2 to reduce load
        - UNHEALTHY: Raises CriticalError to prevent futile requests

    Example:
        >>> # Preferred: use AdapterConfig from YAML
        >>> from bioetl.infrastructure.config import load_source_config
        >>> source_config = load_source_config("chembl")
        >>> adapter_config = source_config.to_adapter_config()
        >>> adapter = ChemblAdapter(
        ...     http_client=http_client,
        ...     logger=logger,
        ...     adapter_config=adapter_config,
        ... )

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    adapter_config: AdapterConfig | None = None
    batch_size: int | None = None  # DEPRECATED: use adapter_config.page_size
    filter_batch_size: int | None = None  # DEPRECATED: use adapter_config.batch_size
    thread_pool: ThreadPoolExecutor | None = None
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="chembl")
    """Provider identifier (required by DataSourcePort)."""

    # Resolved configuration values (computed in __post_init__)
    _page_size: int = field(init=False, default=1000)
    _filter_batch_size: int = field(init=False, default=20)

    # Entity mapper for URL and key resolution
    _mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)

    def __post_init__(self) -> None:
        """Initialize adapter with config values and metrics.

        Configuration priority (RULES.md §12.1.2 - YAML as single source of truth):
        1. adapter_config (from YAML via to_adapter_config())
        2. Explicit batch_size/filter_batch_size parameters (deprecated, for backward compat)
        3. Default fallback values (only if nothing else provided)
        """
        # Resolve configuration with clear priority
        if self.adapter_config is not None:
            # Primary: use AdapterConfig from YAML
            self._page_size = self.adapter_config.page_size
            self._filter_batch_size = self.adapter_config.batch_size
        elif self.batch_size is not None or self.filter_batch_size is not None:
            # Backward compatibility: use explicit parameters
            self._page_size = self.batch_size if self.batch_size is not None else 1000
            self._filter_batch_size = (
                self.filter_batch_size if self.filter_batch_size is not None else 20
            )
        else:
            # Fallback: use domain defaults from AdapterConfig
            default_config = AdapterConfig()
            self._page_size = default_config.page_size
            self._filter_batch_size = default_config.batch_size

        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    def _get_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state.

        Uses circuit breaker failure count for health assessment,
        avoiding duplicate state tracking.

        Returns:
            HealthStatus based on circuit breaker state.
        """
        return assess_health_from_circuit_breaker(self.http_client.circuit_breaker)

    def _get_effective_batch_size(self) -> int:
        """Get batch size adjusted for current health status.

        Uses circuit breaker state for health-aware batching.

        Returns:
            - Normal page_size when HEALTHY
            - Half page_size when DEGRADED (per RULES.md §3.5)

        Raises:
            CriticalError: When UNHEALTHY to prevent futile requests

        """
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

    async def _fetch_page(
        self, url: str, params: dict[str, Any], entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch a single page and handle errors.

        Note: Success/failure tracking is handled by the circuit breaker
        in UnifiedHTTPClient, no duplicate tracking needed here.
        """
        try:
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
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

    async def _fetch_with_filter(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by ID batch with client-side deduplication.

        ChEMBL API pagination can return duplicate records across pages
        when using filter parameters (e.g., assay_chembl_id__in).
        This method deduplicates records by primary key field.
        """
        url = self._mapper.get_resource_url(entity_type)
        offset = 0
        seen_ids: set[str] = set()
        pk_field = self._mapper.get_primary_key_field(entity_type)

        while True:
            params = self._build_params(offset)
            params[f"{filter_field}__in"] = ",".join(id_batch)

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break

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

            if not has_next:
                break
            # Fix: increment by actual records fetched
            offset += len(records)

            if limit and offset >= limit:
                break

    def _handle_error(self, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle fetch errors with unified error handling.

        Uses AdapterErrorHandler for consistent error classification, logging,
        and exception wrapping across all adapters.

        Args:
            e: The exception that occurred
            context: Operation context for logging (e.g., "fetch", "health_check")

        Raises:
            AuthFailureError: For 401/403 authentication failures (CRITICAL)
            RateLimitError: For 429 rate limit errors (RECOVERABLE)
            TimeoutError: For 502/504 gateway errors (RECOVERABLE)
            NetworkError: For other server errors (RECOVERABLE)
        """
        # Use unified error handler for consistent behavior
        self._error_handler.handle_error(
            e,
            context,
            health_status=self._get_health_status().value,
        )

    async def _fetch_filtered(
        self,
        entity_type: str,
        limit: int | None,
        filter_ids: list[str],
        filter_field: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform filtered fetch using ID batches with client-side deduplication."""
        total_fetched = 0
        seen_ids: set[str] = set()
        pk_field = self._mapper.get_primary_key_field(entity_type)

        for id_batch in self._batch_ids(filter_ids, batch_size=self._filter_batch_size):
            async for record in self._fetch_with_filter(
                entity_type, id_batch, filter_field, limit
            ):
                record_id = str(record.get(pk_field, ""))
                if not record_id or record_id not in seen_ids:
                    if record_id:
                        seen_ids.add(record_id)
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
                response = await self.http_client.get(CHEMBL_STATUS_URL)
            return self._handle_health_response(response)
        except Exception as e:
            # Use unified error handler for consistent logging
            self._error_handler.log_error("health_check", e)
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
        self.logger.info(
            "chembl_circuit_breaker_reset",
            provider="chembl",
        )

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
