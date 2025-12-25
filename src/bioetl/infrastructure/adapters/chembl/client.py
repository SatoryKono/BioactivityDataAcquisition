"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.

Uses chembl_webresource_client library for API access.

Error Handling (RULES.md §3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Health-Aware Fetching:
- HEALTHY: Normal batch_size
- DEGRADED: batch_size ÷ 2 (per RULES.md §3.5)
- UNHEALTHY: Fail fast with clear error
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import ChemblApiError, CriticalError
from bioetl.domain.types import ErrorType, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# ChEMBL API base URL
CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status.json"

# Entity type to ChEMBL resource mapping
ENTITY_MAPPING = {
    "activity": "activity",
    "assay": "assay",
    "compound": "molecule",
    "molecule": "molecule",
    "target": "target",
    "target_component": "target_component",
    "document": "document",
    "cell_line": "cell_line",
    "tissue": "tissue",
}

# Plural forms for API response keys (ChEMBL uses irregular plurals)
ENTITY_PLURAL = {
    "activity": "activities",
    "assay": "assays",
    "molecule": "molecules",
    "target": "targets",
    "target_component": "target_components",
    "document": "documents",
    "cell_line": "cell_lines",
    "tissue": "tissues",
}


@dataclass
class ChemblAdapter(BaseHttpAdapter):
    """ChEMBL data source adapter.

    Implements DataSourcePort and FilterableDataSourcePort for fetching
    data from ChEMBL database with optional server-side filtering.

    Args:
        http_client: UnifiedHTTPClient instance
        logger: LoggerPort instance for structured logging
        batch_size: Number of records per API request (default: 1000)
        thread_pool: ThreadPoolExecutor for sync operations

    Health-Aware Behavior:
        - HEALTHY: Uses configured batch_size
        - DEGRADED: Uses batch_size ÷ 2 to reduce load
        - UNHEALTHY: Raises CriticalError to prevent futile requests

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    batch_size: int = 1000
    thread_pool: ThreadPoolExecutor | None = None

    provider_name: str = field(init=False, default="chembl")
    """Provider identifier (required by DataSourcePort)."""

    _consecutive_errors: int = field(init=False, default=0)
    _cached_health: HealthStatus = field(init=False, default=HealthStatus.HEALTHY)
    _error_classifier: ErrorClassifier = field(
        init=False, default_factory=ErrorClassifier
    )
    _total_errors: int = field(init=False, default=0)
    _error_counts: dict[ErrorType, int] = field(init=False, default_factory=dict)

    def _get_resource_url(self, entity_type: str) -> str:
        """Get ChEMBL API URL for entity type."""
        resource = ENTITY_MAPPING.get(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}.json"

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
                f"ChEMBL adapter is UNHEALTHY after {self._consecutive_errors} "
                f"consecutive errors. Total errors: {self._total_errors}"
            )
        if self._cached_health == HealthStatus.DEGRADED:
            reduced = max(100, self.batch_size // 2)  # Minimum 100
            self.logger.warning(
                "chembl_degraded_mode",
                provider="chembl",
                original_batch_size=self.batch_size,
                effective_batch_size=reduced,
                consecutive_errors=self._consecutive_errors,
            )
            return reduced
        return self.batch_size

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
        resource = ENTITY_MAPPING.get(entity_type, entity_type)
        plural_key = ENTITY_PLURAL.get(resource, resource + "s")
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
        """Fetch a single page and handle errors."""
        try:
            response = await self.http_client.get(url, params=params)
            records, has_next = self._process_response(response, entity_type)
            self._consecutive_errors = 0
            return records, has_next
        except Exception as e:
            self._handle_error(e)
            return [], False

    async def _page_iterator(
        self, entity_type: str, limit: int | None = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield pages of records."""
        url = self._get_resource_url(entity_type)
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
        url = self._get_resource_url(entity_type)
        offset = 0
        seen_ids: set[str] = set()
        pk_field = self._get_primary_key_field(entity_type)

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

    def _handle_error(self, e: Exception, context: str = "fetch") -> None:
        """Handle fetch errors with classification and metrics.

        Args:
            e: The exception that occurred
            context: Operation context for logging (e.g., "fetch", "health_check")

        Raises:
            CriticalError: For auth failures and other critical errors
            ChemblApiError: For recoverable and other errors

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
            "chembl_error",
            provider="chembl",
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
                f"Critical ChEMBL error ({error_type.value}): {e}"
            ) from e

        # Wrap in ChemblApiError for consistent handling
        raise ChemblApiError(str(e)) from e

    def _get_primary_key_field(self, entity_type: str) -> str:
        """Get the primary key field name for deduplication."""
        pk_overrides = {
            "assay": "assay_chembl_id",
            "molecule": "molecule_chembl_id",
            "compound": "molecule_chembl_id",
            "document": "document_chembl_id",
            "target": "target_chembl_id",
            "target_component": "component_id",
            "cell_line": "cell_chembl_id",
            "tissue": "tissue_chembl_id",
        }
        return pk_overrides.get(
            entity_type, ENTITY_MAPPING.get(entity_type, entity_type) + "_id"
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
        pk_field = self._get_primary_key_field(entity_type)

        for id_batch in self._batch_ids(filter_ids, batch_size=100):
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
        pk_field = self._get_primary_key_field(entity_type)

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

        Overrides BaseHttpAdapter._probe_health() to use ChEMBL status endpoint
        and internal health state tracking.

        Returns:
            HealthStatus based on status endpoint response or error count.

        """
        try:
            response = await self.http_client.get(CHEMBL_STATUS_URL)
            self._handle_health_response(response)
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

        return self._cached_health

    def _fallback_health_status(self) -> HealthStatus:
        """Return cached health status.

        Overrides BaseHttpAdapter._fallback_health_status() to use
        ChEMBL's internal health state rather than circuit breaker.

        Returns:
            Cached HealthStatus based on consecutive error count.

        """
        return self._cached_health

    def _handle_health_response(self, response: Response) -> None:
        """Process health check response."""
        if response.status_code == 200:
            # Reset error counter on any successful HTTP response
            self._consecutive_errors = 0
            data = response.json()
            if data.get("status") == "UP":
                self._cached_health = HealthStatus.HEALTHY
            else:
                self._cached_health = HealthStatus.DEGRADED
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="status_not_up",
                    api_status=data.get("status"),
                )
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
                "chembl_health_transition",
                provider="chembl",
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
            "error_counts_by_type": {
                k.value: v for k, v in self._error_counts.items()
            },
        }

    def reset_error_counters(self) -> None:
        """Reset error counters (e.g., after successful recovery)."""
        self._consecutive_errors = 0
        self._total_errors = 0
        self._error_counts.clear()
        self._cached_health = HealthStatus.HEALTHY
        self.logger.info(
            "chembl_error_counters_reset",
            provider="chembl",
        )

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities."""
        url = self._get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}
        response = await self.http_client.get(url, params=params)
        data = response.json()
        page_meta = data.get("page_meta", {})
        total_count: int = page_meta.get("total_count", 0)
        return total_count
