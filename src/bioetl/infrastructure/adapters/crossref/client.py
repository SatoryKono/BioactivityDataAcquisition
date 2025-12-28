"""CrossRef data source adapter.

Implements DataSourcePort for CrossRef API.
See RULES.md Appendix A for rate limits and retry strategy.

CrossRef API Documentation: https://api.crossref.org/swagger-ui/index.html

Error Handling (RULES.md §3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Health-Aware Fetching:
- HEALTHY: Normal batch_size
- DEGRADED: batch_size ÷ 2 (per RULES.md §3.5)
- UNHEALTHY: Fail fast with clear error

Rate Limits:
- Without mailto: ~50 req/sec (best effort)
- With mailto (polite pool): 50 req/sec guaranteed

Pagination:
- Uses cursor-based pagination
- cursor=* for first request
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import CriticalError
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import ErrorType, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# CrossRef API constants
CROSSREF_BASE_URL = "https://api.crossref.org"
CROSSREF_WORKS_URL = f"{CROSSREF_BASE_URL}/works"


@dataclass
class CrossRefAdapter(BaseHttpAdapter):
    """CrossRef data source adapter.

    Implements DataSourcePort for fetching publication metadata from CrossRef API.

    Args:
        http_client: UnifiedHTTPClient instance
        logger: LoggerPort instance for structured logging
        batch_size: Number of records per API request (default: 100)
        mailto: Email for polite pool access (recommended)
        metrics: Optional MetricsPort for observability

    Health-Aware Behavior:
        - HEALTHY: Uses configured batch_size
        - DEGRADED: Uses batch_size ÷ 2 to reduce load
        - UNHEALTHY: Raises CriticalError to prevent futile requests

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    batch_size: int = 100
    mailto: str | None = None
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="crossref")
    """Provider identifier (required by DataSourcePort)."""

    _consecutive_errors: int = field(init=False, default=0)
    _cached_health: HealthStatus = field(init=False, default=HealthStatus.HEALTHY)
    _error_classifier: ErrorClassifier = field(
        init=False, default_factory=ErrorClassifier
    )
    _total_errors: int = field(init=False, default=0)
    _error_counts: dict[ErrorType, int] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize adapter metrics after dataclass init."""
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    def _get_effective_batch_size(self) -> int:
        """Get batch size adjusted for current health status.

        Returns:
            - Normal batch_size when HEALTHY
            - Half batch_size when DEGRADED (per RULES.md §3.5)

        Raises:
            CriticalError: When UNHEALTHY to prevent futile requests

        """
        if self._cached_health == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"CrossRef adapter is UNHEALTHY after {self._consecutive_errors} "
                f"consecutive errors. Total errors: {self._total_errors}"
            )
        if self._cached_health == HealthStatus.DEGRADED:
            reduced = max(20, self.batch_size // 2)  # Minimum 20
            self.logger.warning(
                "crossref_degraded_mode",
                provider="crossref",
                original_batch_size=self.batch_size,
                effective_batch_size=reduced,
                consecutive_errors=self._consecutive_errors,
            )
            return reduced
        return self.batch_size

    def _build_params(
        self,
        cursor: str | None = None,
        query: str | None = None,
        filter_param: str | None = None,
    ) -> dict[str, Any]:
        """Build API request parameters with health-aware batch size.

        Args:
            cursor: Cursor for pagination (use '*' for first request)
            query: Optional search query
            filter_param: Optional filter parameter (e.g., 'doi:10.1234/xyz')

        Returns:
            Dictionary of query parameters

        """
        params: dict[str, Any] = {
            "rows": self._get_effective_batch_size(),
        }

        if cursor:
            params["cursor"] = cursor
        else:
            # First request: use '*' for cursor-based pagination
            params["cursor"] = "*"

        if query:
            params["query"] = query

        if filter_param:
            params["filter"] = filter_param

        # Add mailto for polite pool access
        if self.mailto:
            params["mailto"] = self.mailto

        return params

    def _process_response(
        self, response_data: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Process API response, extract records and next cursor.

        Args:
            response_data: JSON response from CrossRef API

        Returns:
            Tuple of (records list, next cursor or None)

        """
        message = response_data.get("message", {})
        records = message.get("items", [])
        next_cursor = message.get("next-cursor")
        return records, next_cursor

    async def _fetch_page(
        self,
        url: str,
        params: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch a single page and handle errors.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            Tuple of (records list, next cursor or None)

        """
        try:
            with self._adapter_metrics.measure_request("/works"):
                response = await self.http_client.get(url, params=params)
            response_data = response.json()
            records, next_cursor = self._process_response(response_data)
            self._consecutive_errors = 0
            return records, next_cursor
        except Exception as e:
            self._handle_error(e)

    async def _page_iterator(
        self,
        query: str | None = None,
        filter_param: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield pages of records with cursor-based pagination.

        Args:
            query: Optional search query
            filter_param: Optional filter parameter
            limit: Maximum total records to fetch

        Yields:
            Lists of record dictionaries

        """
        cursor: str | None = None
        total_fetched = 0

        while True:
            params = self._build_params(
                cursor=cursor,
                query=query,
                filter_param=filter_param,
            )

            # Optimize limit: if we have a global limit
            if limit is not None:
                remaining = limit - total_fetched
                if remaining <= 0:
                    break
                params["rows"] = min(params["rows"], remaining)

            records, next_cursor = await self._fetch_page(CROSSREF_WORKS_URL, params)

            if not records:
                break

            yield records
            total_fetched += len(records)

            if not next_cursor:
                break

            cursor = next_cursor

    async def _fetch_by_dois(
        self,
        dois: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch specific DOIs using filter parameter.

        CrossRef supports batch DOI lookup via filter:
        /works?filter=doi:10.1234/a,doi:10.5678/b,...

        Args:
            dois: List of DOIs to fetch
            limit: Maximum total records to fetch

        Yields:
            Individual record dictionaries

        """
        total_fetched = 0

        # CrossRef allows up to 100 DOIs per batch query
        batch_size = 50  # Conservative to avoid URL length issues

        for i in range(0, len(dois), batch_size):
            if limit is not None and total_fetched >= limit:
                break

            batch = dois[i : i + batch_size]
            # Normalize DOIs and build filter
            normalized = [self._normalize_doi(d) for d in batch]
            filter_param = ",".join(f"doi:{d}" for d in normalized)

            async for records in self._page_iterator(filter_param=filter_param):
                for record in records:
                    yield record
                    total_fetched += 1
                    if limit is not None and total_fetched >= limit:
                        return

    async def _fetch_single_doi(self, doi: str) -> dict[str, Any] | None:
        """Fetch a single work by DOI using direct endpoint.

        Args:
            doi: DOI to fetch

        Returns:
            Work record or None if not found

        """
        normalized = self._normalize_doi(doi)
        url = f"{CROSSREF_WORKS_URL}/{normalized}"

        params: dict[str, Any] = {}
        if self.mailto:
            params["mailto"] = self.mailto

        try:
            with self._adapter_metrics.measure_request(f"/works/{doi}"):
                response = await self.http_client.get(url, params=params)
            response_data = response.json()

            if response_data.get("status") == "ok":
                message: dict[str, Any] = response_data.get("message", {})
                return message
            return None
        except Exception as e:
            error_type = self._error_classifier.classify(e)
            # 404 is expected for missing DOIs
            status_code = getattr(e, "status_code", None)
            if status_code == 404:
                self.logger.debug(
                    "doi_not_found",
                    provider="crossref",
                    doi=doi,
                )
                return None
            self.logger.warning(
                "single_doi_fetch_error",
                provider="crossref",
                doi=doi,
                error=str(e),
                error_type=error_type.value,
            )
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI for API queries.

        Args:
            doi: Raw DOI string

        Returns:
            Normalized DOI (lowercase, stripped, without URL prefix)

        """
        doi = doi.strip().lower()
        # Remove common prefixes
        prefixes = [
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
            "doi:",
        ]
        for prefix in prefixes:
            if doi.startswith(prefix):
                doi = doi[len(prefix) :]
                break
        return doi

    def _handle_error(self, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle fetch errors with classification and metrics.

        Args:
            e: The exception that occurred
            context: Operation context for logging (e.g., "fetch", "health_check")

        Raises:
            CriticalError: For auth failures and other critical errors
            Exception: Re-raises the original exception

        """
        # Classify the error
        error_type = self._error_classifier.classify(e)

        # Update error counters
        self._consecutive_errors += 1
        self._total_errors += 1
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        # Update health status
        self._update_health()

        # Log with full context
        self.logger.error(
            "crossref_error",
            provider="crossref",
            operation=context,
            error=str(e),
            error_type=error_type.value,
            is_critical=error_type.is_critical(),
            is_recoverable=error_type.is_recoverable(),
            consecutive_errors=self._consecutive_errors,
            total_errors=self._total_errors,
            health_status=self._cached_health.value,
        )

        # Critical errors should fail immediately
        if error_type.is_critical():
            raise CriticalError(
                f"Critical CrossRef error ({error_type.value}): {e}"
            ) from e

        # Re-raise for retry handling by UnifiedHTTPClient
        raise

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from CrossRef.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity to fetch (must be 'publication' or 'work')
            limit: Maximum number of records to fetch
            query: Search query for bibliographic search
            filter_ids: List of DOIs to filter by (for deterministic batching)
            filter_field: Field name to filter on (should be 'doi' for CrossRef)

        Yields:
            Dictionary records from CrossRef API

        Raises:
            ValueError: If entity_type is not 'publication' or 'work'

        """
        if entity_type not in ("publication", "work"):
            raise ValueError(
                f"CrossRefAdapter only supports 'publication' or 'work' entity types, "
                f"got: {entity_type}"
            )

        # If filtering by DOIs
        if filter_ids and filter_field == "doi":
            async for record in self._fetch_by_dois(filter_ids, limit):
                yield record
        else:
            # Standard paginated fetch
            total_fetched = 0
            seen_dois: set[str] = set()

            async for records in self._page_iterator(query=query, limit=limit):
                for record in records:
                    doi = record.get("DOI", "")
                    # Deduplicate by DOI
                    if doi and doi.lower() in seen_dois:
                        self.logger.debug(
                            "skipping_duplicate_record",
                            entity_type=entity_type,
                            pk_field="DOI",
                            record_id=doi,
                        )
                        continue
                    if doi:
                        seen_dois.add(doi.lower())

                    yield record
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from CrossRef with ID filtering.

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Type of entity to fetch
            filter_ids: Sorted list of DOIs to filter by
            filter_field: Field name to filter on (should be 'doi')
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching the filter criteria

        """
        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            yield record

    async def _probe_health(self) -> HealthStatus:
        """Perform CrossRef-specific health probe.

        Uses a minimal works query to check API availability.

        Returns:
            HealthStatus based on API response.

        Raises:
            Exception: On request failure (base class handles via _fallback_health_status).

        """
        try:
            params: dict[str, Any] = {"rows": 1}
            if self.mailto:
                params["mailto"] = self.mailto

            with self._adapter_metrics.measure_request("/works/health"):
                response = await self.http_client.get(CROSSREF_WORKS_URL, params=params)

            self._handle_health_response(response)
            return self._cached_health
        except Exception as e:
            self._consecutive_errors += 1
            self._update_health()
            error_type = self._error_classifier.classify(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise  # Let base class handle via _fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Return cached health status.

        Overrides BaseHttpAdapter._fallback_health_status() to use
        CrossRef's internal health state rather than circuit breaker.

        Returns:
            Cached HealthStatus based on consecutive error count.

        """
        return self._cached_health

    def _handle_health_response(self, response: Any) -> None:
        """Process health check response.

        Args:
            response: HTTP response object

        """
        if response.status_code == 200:
            # Reset error counter on successful response
            self._consecutive_errors = 0
            self._cached_health = HealthStatus.HEALTHY
        else:
            self._consecutive_errors += 1
            self._update_health()
            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )

    def _update_health(self) -> None:
        """Update health status based on error count."""
        previous_health = self._cached_health
        if self._consecutive_errors >= 3:
            self._cached_health = HealthStatus.UNHEALTHY
        elif self._consecutive_errors >= 1:
            self._cached_health = HealthStatus.DEGRADED
        else:
            self._cached_health = HealthStatus.HEALTHY

        # Log health transitions
        if previous_health != self._cached_health:
            self.logger.info(
                "crossref_health_transition",
                provider="crossref",
                previous_status=previous_health.value,
                current_status=self._cached_health.value,
                consecutive_errors=self._consecutive_errors,
            )

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics for monitoring.

        Returns:
            Dictionary with error counts and health status.

        """
        return {
            "consecutive_errors": self._consecutive_errors,
            "total_errors": self._total_errors,
            "health_status": self._cached_health.value,
            "error_counts_by_type": {k.value: v for k, v in self._error_counts.items()},
        }

    def reset_error_counters(self) -> None:
        """Reset error counters (e.g., after successful recovery)."""
        self._consecutive_errors = 0
        self._total_errors = 0
        self._error_counts.clear()
        self._cached_health = HealthStatus.HEALTHY
        self.logger.info(
            "crossref_error_counters_reset",
            provider="crossref",
        )

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities.

        Note: CrossRef doesn't provide an exact count endpoint,
        so this makes a minimal query to get the total-results field.

        Args:
            entity_type: Entity type (publication/work)

        Returns:
            Total count of works in CrossRef (approximate)

        """
        params: dict[str, Any] = {"rows": 0}
        if self.mailto:
            params["mailto"] = self.mailto

        with self._adapter_metrics.measure_request("/works/count"):
            response = await self.http_client.get(CROSSREF_WORKS_URL, params=params)
        data = response.json()
        message = data.get("message", {})
        total_count: int = message.get("total-results", 0)
        return total_count
