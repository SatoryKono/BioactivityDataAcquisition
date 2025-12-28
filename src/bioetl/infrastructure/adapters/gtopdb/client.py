"""GtoPdb (Guide to Pharmacology) data source adapter.

Implements DataSourcePort for GtoPdb REST API.
See RULES.md Appendix A for rate limits and retry strategy.

API Documentation: https://www.guidetopharmacology.org/webServices.jsp

Error Handling (RULES.md 3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Health-Aware Fetching:
- HEALTHY: Normal batch_size
- DEGRADED: batch_size / 2 (per RULES.md 3.5)
- UNHEALTHY: Fail fast with clear error
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

    from httpx import Response

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# GtoPdb API base URL and endpoints
GTOPDB_BASE_URL = "https://www.guidetopharmacology.org/services"

# Entity type to endpoint mapping
ENTITY_ENDPOINTS = {
    "target": "/targets",
    "targets": "/targets",
    "ligand": "/ligands",
    "ligands": "/ligands",
    "interaction": "/interactions",
    "interactions": "/interactions",
    "family": "/targets/families",
    "families": "/targets/families",
}

# Entity type to ID field mapping
ENTITY_ID_FIELDS = {
    "target": "targetId",
    "targets": "targetId",
    "ligand": "ligandId",
    "ligands": "ligandId",
    "interaction": "interactionId",
    "interactions": "interactionId",
    "family": "familyId",
    "families": "familyId",
}


class GtopdbApiError(Exception):
    """Exception raised for GtoPdb API errors."""

    pass


@dataclass
class GtopdbAdapter(BaseHttpAdapter):
    """GtoPdb data source adapter.

    Implements DataSourcePort for fetching data from GtoPdb REST API.

    Args:
        http_client: UnifiedHTTPClient instance
        logger: LoggerPort instance for structured logging
        batch_size: Number of records per API request (default: 100)
        base_url: Base URL for GtoPdb API

    Health-Aware Behavior:
        - HEALTHY: Uses configured batch_size
        - DEGRADED: Uses batch_size / 2 to reduce load
        - UNHEALTHY: Raises CriticalError to prevent futile requests
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    batch_size: int = 100
    base_url: str = GTOPDB_BASE_URL
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="gtopdb")
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

    def _get_endpoint(self, entity_type: str) -> str:
        """Get API endpoint for entity type."""
        endpoint = ENTITY_ENDPOINTS.get(entity_type.lower())
        if not endpoint:
            raise ValueError(
                f"Unknown entity type: {entity_type}. "
                f"Available: {list(ENTITY_ENDPOINTS.keys())}"
            )
        return endpoint

    def _get_id_field(self, entity_type: str) -> str:
        """Get ID field name for entity type."""
        id_field = ENTITY_ID_FIELDS.get(entity_type.lower())
        if not id_field:
            return "id"
        return id_field

    def _get_effective_batch_size(self) -> int:
        """Get batch size adjusted for current health status.

        Returns:
            - Normal batch_size when HEALTHY
            - Half batch_size when DEGRADED (per RULES.md 3.5)

        Raises:
            CriticalError: When UNHEALTHY to prevent futile requests.
        """
        if self._cached_health == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"GtoPdb adapter is UNHEALTHY after {self._consecutive_errors} "
                f"consecutive errors. Total errors: {self._total_errors}"
            )
        if self._cached_health == HealthStatus.DEGRADED:
            reduced = max(10, self.batch_size // 2)
            self.logger.warning(
                "gtopdb_degraded_mode",
                provider="gtopdb",
                original_batch_size=self.batch_size,
                effective_batch_size=reduced,
                consecutive_errors=self._consecutive_errors,
            )
            return reduced
        return self.batch_size

    def _build_url(self, entity_type: str) -> str:
        """Build full URL for entity type."""
        endpoint = self._get_endpoint(entity_type)
        return f"{self.base_url}{endpoint}"

    def _process_response(self, response: Response) -> list[dict[str, Any]]:
        """Process API response and extract records.

        GtoPdb API returns a JSON array directly (no pagination wrapper).
        """
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Some endpoints return a single object
            return [data]
        return []

    async def _fetch_page(
        self, url: str, params: dict[str, Any], entity_type: str
    ) -> list[dict[str, Any]]:
        """Fetch a single page and handle errors."""
        try:
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
            records = self._process_response(response)
            self._consecutive_errors = 0
            return records
        except Exception as e:
            self._handle_error(e)

    async def _fetch_all(
        self, entity_type: str, limit: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch all records for entity type.

        GtoPdb API returns all records in one response (no pagination).
        We still respect the limit parameter.
        """
        url = self._build_url(entity_type)
        id_field = self._get_id_field(entity_type)

        records = await self._fetch_page(url, {}, entity_type)

        total_fetched = 0
        seen_ids: set[str] = set()

        for record in records:
            record_id = str(record.get(id_field, ""))

            # Deduplicate
            if record_id and record_id in seen_ids:
                self.logger.debug(
                    "skipping_duplicate_record",
                    entity_type=entity_type,
                    record_id=record_id,
                )
                continue

            if record_id:
                seen_ids.add(record_id)

            yield record
            total_fetched += 1

            if limit and total_fetched >= limit:
                return

    async def _fetch_by_id(
        self, entity_type: str, entity_id: int | str
    ) -> dict[str, Any] | None:
        """Fetch a single entity by ID."""
        url = f"{self._build_url(entity_type)}/{entity_id}"
        try:
            with self._adapter_metrics.measure_request(f"/{entity_type}/{entity_id}"):
                response = await self.http_client.get(url)
            if response.status_code == 404:
                return None
            data = response.json()
            self._consecutive_errors = 0
            return data if isinstance(data, dict) else None
        except Exception as e:
            # 404 is not an error for single entity fetch
            if hasattr(e, "response") and getattr(e.response, "status_code", 0) == 404:
                return None
            self._handle_error(e)

    def _handle_error(self, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle fetch errors with classification and metrics.

        Args:
            e: The exception that occurred
            context: Operation context for logging

        Raises:
            CriticalError: For auth failures and other critical errors
            GtopdbApiError: For recoverable and other errors
        """
        error_type = self._error_classifier.classify(e)

        self._consecutive_errors += 1
        self._total_errors += 1
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        self._update_health()

        self.logger.error(
            "gtopdb_error",
            provider="gtopdb",
            operation=context,
            error=str(e),
            error_type=error_type.value,
            is_critical=error_type.is_critical(),
            is_recoverable=error_type.is_recoverable(),
            consecutive_errors=self._consecutive_errors,
            total_errors=self._total_errors,
            health_status=self._cached_health.value,
        )

        if error_type.is_critical():
            raise CriticalError(
                f"Critical GtoPdb error ({error_type.value}): {e}"
            ) from e

        raise GtopdbApiError(str(e)) from e

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from GtoPdb.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity to fetch (target, ligand, interaction)
            limit: Maximum number of records to fetch
            query: Unused for GtoPdb (no search API)
            filter_ids: List of IDs to filter by
            filter_field: Field name to filter on (unused, uses entity ID)

        Yields:
            Dictionary records from GtoPdb API.
        """
        if filter_ids:
            # Fetch specific entities by ID
            total_fetched = 0
            for entity_id in filter_ids:
                record = await self._fetch_by_id(entity_type, entity_id)
                if record:
                    yield record
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return
        else:
            # Fetch all entities
            async for record in self._fetch_all(entity_type, limit):
                yield record

    async def _probe_health(self) -> HealthStatus:
        """Perform GtoPdb-specific health probe.

        Uses a lightweight targets request with limit=1.
        """
        try:
            url = f"{self.base_url}/targets"
            params = {"limit": 1}
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get(url, params=params)
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
            raise

    def _fallback_health_status(self) -> HealthStatus:
        """Return cached health status."""
        return self._cached_health

    def _handle_health_response(self, response: Response) -> None:
        """Process health check response."""
        if response.status_code == 200:
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

        if previous_health != self._cached_health:
            self.logger.info(
                "gtopdb_health_transition",
                provider="gtopdb",
                previous_status=previous_health.value,
                current_status=self._cached_health.value,
                consecutive_errors=self._consecutive_errors,
            )

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "consecutive_errors": self._consecutive_errors,
            "total_errors": self._total_errors,
            "health_status": self._cached_health.value,
            "error_counts_by_type": {k.value: v for k, v in self._error_counts.items()},
        }

    def reset_error_counters(self) -> None:
        """Reset error counters."""
        self._consecutive_errors = 0
        self._total_errors = 0
        self._error_counts.clear()
        self._cached_health = HealthStatus.HEALTHY
        self.logger.info(
            "gtopdb_error_counters_reset",
            provider="gtopdb",
        )

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities.

        GtoPdb doesn't have a count endpoint, so we fetch all and count.
        This is cached after first call.
        """
        url = self._build_url(entity_type)
        with self._adapter_metrics.measure_request(f"/{entity_type}/count"):
            response = await self.http_client.get(url)
        records = self._process_response(response)
        return len(records)
