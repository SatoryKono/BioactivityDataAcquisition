"""CrossRef data source adapter.

Implements DataSourcePort for CrossRef API.
See RULES.md Appendix A for rate limits and retry strategy.

Uses httpx directly for REST/JSON API access.

Error Handling (RULES.md §3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Polite Pool:
- CrossRef provides higher rate limits (50 req/sec) when `mailto` is provided
- Always send mailto in User-Agent or query parameters
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import CrossRefApiError
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

CROSSREF_API_BASE = "https://api.crossref.org"


@dataclass
class CrossRefAdapter(BaseHttpAdapter):
    """CrossRef data source adapter.

    Inherits from BaseHttpAdapter for standardized lifecycle management
    and Template Method pattern for health checks.

    Implements DataSourcePort and FilterableDataSourcePort for CrossRef
    metadata extraction with batch DOI resolution support.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        mailto: Technical email for polite pool access (required).
            CrossRef provides higher rate limits (50 req/sec) with mailto.
            See: https://github.com/CrossRef/rest-api-doc#good-manners--more-reliable-service
        batch_size: Number of DOIs per batch request (max 100).
        metrics: Optional MetricsPort for recording adapter metrics.

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    mailto: str
    batch_size: int = 50
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="crossref")
    """Provider identifier (required by DataSourcePort)."""

    def __post_init__(self) -> None:
        """Initialize adapter metrics after dataclass init."""
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with polite pool identification."""
        return {
            "User-Agent": f"BioETL/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI to lowercase, stripped format."""
        return doi.strip().lower()

    async def _fetch_single_work(self, doi: str) -> dict[str, Any] | None:
        """Fetch a single work by DOI.

        Args:
            doi: The DOI to fetch (will be normalized).

        Returns:
            Work record or None if not found.

        Raises:
            CrossRefApiError: On API errors (non-404).

        """
        normalized_doi = self._normalize_doi(doi)
        url = f"{CROSSREF_API_BASE}/works/{normalized_doi}"

        try:
            with self._adapter_metrics.measure_request("/works/{doi}"):
                response = await self.http_client.get(
                    url, headers=self._build_headers()
                )

            if response.status_code == 404:
                self.logger.debug(
                    "crossref_doi_not_found",
                    doi=normalized_doi,
                )
                return None

            if response.status_code != 200:
                raise CrossRefApiError(
                    f"CrossRef API error for DOI {normalized_doi}",
                    status_code=response.status_code,
                )

            data = response.json()
            work: dict[str, Any] = data.get("message", {})
            return work

        except CrossRefApiError:
            raise
        except Exception as e:
            self.logger.error(
                "crossref_fetch_failed",
                doi=normalized_doi,
                error=str(e),
            )
            raise CrossRefApiError(f"Failed to fetch DOI {normalized_doi}: {e}") from e

    async def _fetch_batch_works(
        self, dois: list[str]
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch multiple works by DOI batch.

        Uses CrossRef filter endpoint for batch resolution.

        Args:
            dois: List of DOIs to fetch (max 100).

        Yields:
            Work records for found DOIs.

        """
        if not dois:
            return

        # CrossRef allows filtering by multiple DOIs
        normalized_dois = [self._normalize_doi(d) for d in dois]
        filter_value = ",".join(normalized_dois)
        url = f"{CROSSREF_API_BASE}/works"
        params = {
            "filter": f"doi:{filter_value}",
            "rows": str(len(normalized_dois)),
            "mailto": self.mailto,
        }

        try:
            with self._adapter_metrics.measure_request("/works?filter=doi"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )

            if response.status_code != 200:
                self.logger.warning(
                    "crossref_batch_fetch_failed",
                    status_code=response.status_code,
                    doi_count=len(dois),
                )
                # Fall back to individual fetches
                for doi in dois:
                    work = await self._fetch_single_work(doi)
                    if work:
                        yield work
                return

            data = response.json()
            items = data.get("message", {}).get("items", [])
            for item in items:
                yield item

        except Exception as e:
            self.logger.warning(
                "crossref_batch_fetch_error",
                error=str(e),
                doi_count=len(dois),
            )
            # Fall back to individual fetches on error
            for doi in dois:
                try:
                    work = await self._fetch_single_work(doi)
                    if work:
                        yield work
                except Exception as inner_e:
                    self.logger.debug(
                        "crossref_individual_fetch_failed",
                        doi=doi,
                        error=str(inner_e),
                    )

    async def _search_works(
        self,
        query: str,
        limit: int | None = None,
        cursor: str = "*",
    ) -> AsyncIterator[dict[str, Any]]:
        """Search for works using cursor-based pagination.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            cursor: Pagination cursor (* for first page).

        Yields:
            Work records matching the query.

        """
        url = f"{CROSSREF_API_BASE}/works"
        rows = min(limit, 100) if limit else 100
        fetched = 0

        while True:
            params = {
                "query": query,
                "rows": str(rows),
                "cursor": cursor,
                "mailto": self.mailto,
            }

            try:
                with self._adapter_metrics.measure_request("/works?query"):
                    response = await self.http_client.get(
                        url, params=params, headers=self._build_headers()
                    )

                if response.status_code != 200:
                    raise CrossRefApiError(
                        f"CrossRef search failed: {response.status_code}",
                        status_code=response.status_code,
                    )

                data = response.json()
                message = data.get("message", {})
                items = message.get("items", [])

                if not items:
                    break

                for item in items:
                    yield item
                    fetched += 1
                    if limit and fetched >= limit:
                        return

                # Get next cursor
                next_cursor = message.get("next-cursor")
                if not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor

            except CrossRefApiError:
                raise
            except Exception as e:
                self.logger.error(
                    "crossref_search_failed",
                    query=query,
                    error=str(e),
                )
                raise CrossRefApiError(f"CrossRef search failed: {e}") from e

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch CrossRef works by DOI list (batch resolution).

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Must be 'work' or 'publication'.
            filter_ids: List of DOIs to resolve.
            filter_field: Field name (expected 'doi').
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each resolved work.

        Raises:
            ValueError: If entity_type is not 'work' or 'publication'.

        """
        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"CrossRefAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                msg="CrossRef only supports DOI filtering, assuming DOIs",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0

        # Process DOIs in batches (max 100 per request)
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]
            async for work in self._fetch_batch_works(batch):
                yield work
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch CrossRef works.

        Implements DataSourcePort.fetch().

        Args:
            entity_type: Must be 'work' or 'publication'.
            limit: Maximum number of records to fetch.
            query: Search query for CrossRef (optional).
            filter_ids: List of DOIs to resolve (optional).
            filter_field: Field name for filtering (expected 'doi').

        Yields:
            Dictionary records from CrossRef API.

        Raises:
            ValueError: If entity_type is invalid.
            CrossRefApiError: On API errors.

        """
        if filter_ids:
            effective_filter_field = filter_field or "doi"
            async for work in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield work
            return

        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"CrossRefAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if not query:
            raise ValueError(
                "CrossRef requires either filter_ids (DOIs) or query parameter"
            )

        async for work in self._search_works(query, limit):
            yield work

    async def _probe_health(self) -> HealthStatus:
        """Perform CrossRef-specific health probe.

        Overrides BaseHttpAdapter._probe_health() to use CrossRef works endpoint.

        Returns:
            HealthStatus.HEALTHY - API accessible
            HealthStatus.DEGRADED - slow response (>5 sec)
            HealthStatus.UNHEALTHY - non-200 response

        Raises:
            Exception: On request failure (logged before raising).

        """
        try:
            url = f"{CROSSREF_API_BASE}/works"
            params = {
                "rows": "1",
                "mailto": self.mailto,
            }

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )
            elapsed = time.monotonic() - start_time

            if response.status_code != 200:
                self.logger.warning(
                    "crossref_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            # Slow response = degraded
            if elapsed > 5.0:
                self.logger.warning(
                    "crossref_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.warning(
                "crossref_health_check_failed",
                error=str(e),
            )
            raise  # Let health_check() return _fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get fallback health status on probe failure.

        Overrides BaseHttpAdapter._fallback_health_status().

        Returns:
            HealthStatus.UNHEALTHY

        """
        return HealthStatus.UNHEALTHY

    async def aclose(self) -> None:
        """Close adapter resources.

        Overrides BaseHttpAdapter.aclose() to properly close the HTTP client.
        Safely closes via the public context manager interface.
        Idempotent - safe to call multiple times.
        """
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


def _create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,
) -> CrossRefAdapter:
    """Custom creator for CrossRef adapter.

    Handles logic for obtaining mailto from settings.

    Args:
        http_client: HTTP client
        logger: Logger
        settings: Application settings
        **kwargs: Additional parameters (mailto, batch_size, metrics)

    Returns:
        Initialized CrossRefAdapter

    Raises:
        ValueError: If mailto is not provided and not found in settings

    """
    # Mailto: from kwargs or settings
    mailto = kwargs.get("mailto")
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )

    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")

    return CrossRefAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
    )
