"""OpenAlex data source adapter.

Implements DataSourcePort for OpenAlex - an open catalog of scholarly works.
See https://docs.openalex.org/ for API documentation.

Rate Limits (Polite Pool):
- 10 requests/second with mailto parameter
- Without mailto: lower limits apply

Pagination:
- Cursor-based pagination (cursor=* for first page)
- Up to 200 results per page

Health Check:
- Generic probe: GET /works?per_page=1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, NoReturn

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import CriticalError, OpenAlexApiError
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import ErrorType, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.openalex.abstract_parser import (
    reconstruct_abstract,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from httpx import Response

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# OpenAlex API configuration
OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_DEFAULT_PER_PAGE = 200
OPENALEX_MAX_FILTER_IDS = 50  # Max DOIs in single OR filter


@dataclass
class OpenAlexAdapter(BaseHttpAdapter, PaginatedFetcherMixin):
    """OpenAlex data source adapter.

    Implements DataSourcePort and FilterableDataSourcePort for fetching
    scholarly works, authors, institutions, and other entities from OpenAlex.

    Args:
        http_client: UnifiedHTTPClient instance for HTTP requests.
        logger: LoggerPort instance for structured logging.
        mailto: Email for polite pool access (10 req/sec).
        per_page: Results per page (max 200).
        metrics: Optional MetricsPort for observability.

    Polite Pool:
        Including `mailto` parameter grants higher rate limits.
        See https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication

    Cursor-Based Pagination:
        OpenAlex uses cursor-based pagination for stable results.
        First page: cursor=*
        Subsequent: cursor=<value from meta.next_cursor>

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    mailto: str | None = None
    per_page: int = OPENALEX_DEFAULT_PER_PAGE
    base_url: str = OPENALEX_BASE_URL
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="openalex")
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

    def _get_effective_per_page(self) -> int:
        """Get per_page adjusted for current health status.

        Returns:
            - Normal per_page when HEALTHY
            - Half per_page when DEGRADED

        Raises:
            CriticalError: When UNHEALTHY to prevent futile requests

        """
        if self._cached_health == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"OpenAlex adapter is UNHEALTHY after {self._consecutive_errors} "
                f"consecutive errors. Total errors: {self._total_errors}"
            )
        if self._cached_health == HealthStatus.DEGRADED:
            reduced = max(25, self.per_page // 2)
            self.logger.warning(
                "openalex_degraded_mode",
                provider="openalex",
                original_per_page=self.per_page,
                effective_per_page=reduced,
                consecutive_errors=self._consecutive_errors,
            )
            return reduced
        return self.per_page

    def _build_base_params(self) -> dict[str, Any]:
        """Build base API parameters including mailto for polite pool."""
        params: dict[str, Any] = {}
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    @staticmethod
    def _format_date_filter(dt: date | datetime | str) -> str:
        """Format date for OpenAlex filter.

        OpenAlex accepts dates in YYYY-MM-DD format for filters like:
        - from_updated_date:2023-01-01
        - from_publication_date:2023-01-01

        Args:
            dt: Date as date object, datetime object, or ISO string.

        Returns:
            Date string in YYYY-MM-DD format.

        """
        if isinstance(dt, datetime):
            return dt.date().isoformat()
        if isinstance(dt, date):
            return dt.isoformat()
        # Assume string is already in correct format or close to it
        return str(dt)[:10]  # Take first 10 chars (YYYY-MM-DD)

    def _get_entity_endpoint(self, entity_type: str) -> str:
        """Get API endpoint URL for entity type.

        Args:
            entity_type: Type of entity (works, authors, institutions, etc.)

        Returns:
            Full URL for the entity endpoint.

        """
        return f"{self.base_url}/{entity_type}"

    def _extract_openalex_id(self, url: str | None) -> str | None:
        """Extract OpenAlex ID from full URL.

        Args:
            url: Full OpenAlex URL like https://openalex.org/W2741809807

        Returns:
            Just the ID part (e.g., W2741809807)

        """
        if not url:
            return None
        # URL format: https://openalex.org/W2741809807
        return url.split("/")[-1] if "/" in url else url

    def _transform_work(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform OpenAlex work record to normalized format.

        Handles:
        - ID extraction from URLs
        - Abstract reconstruction from inverted index
        - Author/institution extraction

        Args:
            record: Raw work record from OpenAlex API.

        Returns:
            Transformed record with normalized fields.

        """
        transformed = dict(record)  # Create a copy

        # Extract OpenAlex ID from URL
        if "id" in record:
            transformed["openalex_id"] = self._extract_openalex_id(record["id"])

        # Extract DOI without prefix
        doi = record.get("doi")
        if doi and doi.startswith("https://doi.org/"):
            transformed["doi"] = doi[len("https://doi.org/"):]
        elif doi:
            transformed["doi"] = doi

        # Extract PMID from ids if present
        ids = record.get("ids", {})
        if ids and "pmid" in ids:
            pmid = ids["pmid"]
            if pmid and pmid.startswith("https://pubmed.ncbi.nlm.nih.gov/"):
                transformed["pmid"] = pmid.split("/")[-1]
            else:
                transformed["pmid"] = pmid

        # Reconstruct abstract from inverted index
        abstract_index = record.get("abstract_inverted_index")
        if abstract_index:
            transformed["abstract"] = reconstruct_abstract(abstract_index)

        # Extract author names
        authorships = record.get("authorships", [])
        if authorships:
            authors = []
            institutions = []
            for authorship in authorships:
                author = authorship.get("author", {})
                if author and author.get("display_name"):
                    authors.append(author["display_name"])
                # Collect institutions
                for inst in authorship.get("institutions", []):
                    if inst and inst.get("display_name"):
                        institutions.append(inst["display_name"])
            transformed["authors"] = authors
            transformed["institutions"] = list(set(institutions))

        # Extract journal name from primary location
        primary_location = record.get("primary_location", {})
        if primary_location:
            source = primary_location.get("source", {})
            if source and source.get("display_name"):
                transformed["journal"] = source["display_name"]

        # Extract concept names
        concepts = record.get("concepts", [])
        if concepts:
            transformed["concept_names"] = [
                c.get("display_name") for c in concepts if c.get("display_name")
            ]

        # Map type to doc_type
        work_type = record.get("type")
        if work_type:
            transformed["doc_type"] = self._map_work_type(work_type)

        # Extract open access status
        oa_info = record.get("open_access", {})
        if oa_info:
            transformed["is_open_access"] = oa_info.get("is_oa", False)

        return transformed

    def _map_work_type(self, work_type: str) -> str:
        """Map OpenAlex work type to standard doc_type.

        Args:
            work_type: OpenAlex type (article, book, etc.)

        Returns:
            Standardized document type.

        """
        type_mapping = {
            "article": "PUBLICATION",
            "book": "BOOK",
            "book-chapter": "BOOK_CHAPTER",
            "dataset": "DATASET",
            "dissertation": "DISSERTATION",
            "editorial": "EDITORIAL",
            "erratum": "ERRATUM",
            "letter": "LETTER",
            "paratext": "PARATEXT",
            "peer-review": "PEER_REVIEW",
            "preprint": "PREPRINT",
            "report": "REPORT",
            "review": "REVIEW",
            "standard": "STANDARD",
        }
        return type_mapping.get(work_type, work_type.upper())

    async def _fetch_page(
        self,
        url: str,
        params: dict[str, Any],
        entity_type: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch a single page and return records with next cursor.

        Args:
            url: API endpoint URL.
            params: Query parameters.
            entity_type: Entity type for logging.

        Returns:
            Tuple of (records, next_cursor).

        """
        try:
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
            return self._process_response(response)
        except Exception as e:
            self._handle_error(e)

    def _process_response(
        self, response: Response
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Process API response and extract records and next cursor.

        Args:
            response: HTTP response from OpenAlex API.

        Returns:
            Tuple of (results list, next_cursor or None).

        """
        data = response.json()
        results = data.get("results", [])
        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")

        # Reset error counter on success
        self._consecutive_errors = 0

        return results, next_cursor

    def _handle_error(self, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle fetch errors with classification and metrics.

        Args:
            e: The exception that occurred.
            context: Operation context for logging.

        Raises:
            CriticalError: For auth failures and critical errors.
            OpenAlexApiError: For other errors.

        """
        error_type = self._error_classifier.classify(e)

        self._consecutive_errors += 1
        self._total_errors += 1
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        self._update_health()

        self.logger.error(
            "openalex_error",
            provider="openalex",
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
                f"Critical OpenAlex error ({error_type.value}): {e}"
            ) from e

        raise OpenAlexApiError(str(e)) from e

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
                "openalex_health_transition",
                provider="openalex",
                previous_status=previous_health.value,
                current_status=self._cached_health.value,
                consecutive_errors=self._consecutive_errors,
            )

    async def _fetch_standard(
        self,
        entity_type: str,
        limit: int | None,
        query: str | None = None,
        from_updated_date: date | datetime | str | None = None,
        from_publication_date: date | datetime | str | None = None,
        additional_filters: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform standard cursor-based paginated fetch.

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum records to fetch.
            query: Optional search query.
            from_updated_date: Only fetch records updated on or after this date.
                Useful for incremental fetches (RULES.md incremental support).
            from_publication_date: Only fetch records published on or after this date.
            additional_filters: Additional filter key-value pairs.

        Yields:
            Records from OpenAlex API.

        """
        url = self._get_entity_endpoint(entity_type)

        # Build filter string from date parameters
        filter_parts: list[str] = []
        if from_updated_date:
            date_str = self._format_date_filter(from_updated_date)
            filter_parts.append(f"from_updated_date:{date_str}")
        if from_publication_date:
            date_str = self._format_date_filter(from_publication_date)
            filter_parts.append(f"from_publication_date:{date_str}")
        if additional_filters:
            for key, value in additional_filters.items():
                filter_parts.append(f"{key}:{value}")

        combined_filter = ",".join(filter_parts) if filter_parts else None

        async def _pagination_callback(
            cursor: str | None,
            fetched: int,
            filter_string: str | None = combined_filter,
        ) -> tuple[list[dict[str, Any]], str | None]:
            params = self._build_base_params()
            params["per_page"] = self._get_effective_per_page()

            # Cursor-based pagination
            if cursor is None:
                params["cursor"] = "*"  # First page
            else:
                params["cursor"] = cursor

            # Optional search filter
            if query:
                params["search"] = query

            # Add combined filter if present
            if filter_string:
                params["filter"] = filter_string

            results, next_cursor = await self._fetch_page(url, params, entity_type)

            # Transform works if entity_type is 'works'
            if entity_type == "works":
                results = [self._transform_work(r) for r in results]

            return results, next_cursor

        # Use pagination mixin
        async for item in self.paginated_fetch(
            _pagination_callback,
            limit=limit,
            initial_cursor=None,
        ):
            yield item

    def _build_filter_string(
        self, filter_ids: list[str], filter_field: str
    ) -> str:
        """Build OpenAlex filter string for batch filtering.

        OpenAlex uses pipe (|) for OR conditions within a filter.
        Example: filter=doi:10.1234/a|10.1234/b|10.1234/c

        Args:
            filter_ids: List of IDs to filter by.
            filter_field: Field name (doi, openalex_id, etc.)

        Returns:
            Filter string for API query.

        """
        # Map common field names to OpenAlex filter names
        field_mapping = {
            "doi": "doi",
            "openalex_id": "ids.openalex",
            "pmid": "ids.pmid",
        }
        api_field = field_mapping.get(filter_field, filter_field)

        # Join IDs with pipe for OR condition
        joined_ids = "|".join(filter_ids)
        return f"{api_field}:{joined_ids}"

    async def _fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by IDs.

        OpenAlex supports up to ~50 values in an OR filter.
        This method batches IDs accordingly.

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of IDs to filter by.
            filter_field: Field name to filter on.
            limit: Maximum records to fetch.

        Yields:
            Records matching the filter criteria.

        """
        url = self._get_entity_endpoint(entity_type)
        total_fetched = 0

        # Process IDs in batches
        for i in range(0, len(filter_ids), OPENALEX_MAX_FILTER_IDS):
            if limit and total_fetched >= limit:
                break

            batch = filter_ids[i : i + OPENALEX_MAX_FILTER_IDS]
            batch_filter_string = self._build_filter_string(batch, filter_field)

            async def _pagination_callback(
                cursor: str | None,
                fetched: int,
                filter_string: str = batch_filter_string,
            ) -> tuple[list[dict[str, Any]], str | None]:
                params = self._build_base_params()
                params["per_page"] = self._get_effective_per_page()
                params["filter"] = filter_string

                if cursor is None:
                    params["cursor"] = "*"
                else:
                    params["cursor"] = cursor

                results, next_cursor = await self._fetch_page(
                    url, params, entity_type
                )

                if entity_type == "works":
                    results = [self._transform_work(r) for r in results]

                return results, next_cursor

            async for item in self.paginated_fetch(
                _pagination_callback,
                limit=limit - total_fetched if limit else None,
                initial_cursor=None,
            ):
                yield item
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
        from_updated_date: date | datetime | str | None = None,
        from_publication_date: date | datetime | str | None = None,
        additional_filters: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from OpenAlex.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity (works, authors, institutions, etc.)
            limit: Maximum number of records to fetch.
            query: Optional search query.
            filter_ids: Optional list of IDs to filter by.
            filter_field: Field name to filter on.
            from_updated_date: Only fetch records updated on or after this date.
                Useful for incremental fetches.
            from_publication_date: Only fetch records published on or after this date.
            additional_filters: Additional filter key-value pairs.

        Yields:
            Dictionary records from OpenAlex API.

        """
        if filter_ids and filter_field:
            async for record in self._fetch_filtered(
                entity_type, filter_ids, filter_field, limit
            ):
                yield record
        else:
            async for record in self._fetch_standard(
                entity_type,
                limit,
                query,
                from_updated_date=from_updated_date,
                from_publication_date=from_publication_date,
                additional_filters=additional_filters,
            ):
                yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by IDs.

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: Sorted list of IDs to filter by.
            filter_field: Field name to filter on.
            limit: Maximum records to fetch.

        Yields:
            Records matching the filter criteria.

        """
        async for record in self._fetch_filtered(
            entity_type, filter_ids, filter_field, limit
        ):
            yield record

    async def _probe_health(self) -> HealthStatus:
        """Perform OpenAlex-specific health probe.

        Uses a lightweight works query to check API availability.

        Returns:
            HealthStatus based on API response.

        """
        try:
            url = f"{self.base_url}/works"
            params = self._build_base_params()
            params["per_page"] = 1

            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                self._consecutive_errors = 0
                self._cached_health = HealthStatus.HEALTHY
                return HealthStatus.HEALTHY

            self._consecutive_errors += 1
            self._update_health()
            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )
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
        """Return cached health status as fallback.

        Returns:
            Cached HealthStatus based on consecutive error count.

        """
        return self._cached_health

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
            "openalex_error_counters_reset",
            provider="openalex",
        )
