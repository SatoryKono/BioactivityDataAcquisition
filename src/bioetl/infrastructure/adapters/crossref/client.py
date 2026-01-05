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

from bioetl.domain.normalization import normalize_doi
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError

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

    async def _fetch_single_publication(self, doi: str) -> dict[str, Any] | None:
        """Fetch a single publication by DOI.

        Args:
            doi: The DOI to fetch (will be normalized).

        Returns:
            Publication record or None if not found.

        Raises:
            CrossRefApiError: On API errors (non-404).

        """
        normalized_doi = normalize_doi(doi) or ""
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
            publication: dict[str, Any] = data.get("message", {})
            return publication

        except CrossRefApiError:
            raise
        except Exception as e:
            self.logger.error(
                "crossref_fetch_failed",
                doi=normalized_doi,
                error=str(e),
            )
            raise CrossRefApiError(f"Failed to fetch DOI {normalized_doi}: {e}") from e

    async def _fallback_individual_fetch(
        self, dois: list[str]
    ) -> AsyncIterator[dict[str, Any]]:
        """Fall back to individual DOI fetches.

        Used when batch endpoint fails.

        Args:
            dois: List of DOIs to fetch individually.

        Yields:
            Publication records for successfully fetched DOIs.

        """
        for doi in dois:
            try:
                publication = await self._fetch_single_publication(doi)
                if publication:
                    yield publication
            except Exception as e:
                self.logger.debug(
                    "crossref_individual_fetch_failed",
                    doi=doi,
                    error=str(e),
                )

    async def _fetch_batch_publications(
        self, dois: list[str]
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch multiple publications by DOI batch.

        Uses CrossRef filter endpoint for batch resolution.

        Args:
            dois: List of DOIs to fetch (max 100).

        Yields:
            Publication records for found DOIs.

        """
        if not dois:
            return

        # CrossRef allows filtering by multiple DOIs
        normalized_dois = [normalize_doi(d) or "" for d in dois]
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
                async for publication in self._fallback_individual_fetch(dois):
                    yield publication
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
            async for publication in self._fallback_individual_fetch(dois):
                yield publication

    async def _fetch_search_page(
        self,
        query: str,
        rows: int,
        cursor: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch a single page of search results.

        Args:
            query: Search query string.
            rows: Number of results per page.
            cursor: Pagination cursor.

        Returns:
            Tuple of (items list, next_cursor or None).

        Raises:
            CrossRefApiError: On API errors.

        """
        url = f"{CROSSREF_API_BASE}/works"
        params = {
            "query": query,
            "rows": str(rows),
            "cursor": cursor,
            "mailto": self.mailto,
        }

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
        next_cursor = message.get("next-cursor")

        return items, next_cursor

    def _should_continue_pagination(
        self, items: list[dict[str, Any]], next_cursor: str | None, current_cursor: str
    ) -> bool:
        """Check if pagination should continue.

        Args:
            items: Items from current page.
            next_cursor: Next cursor from response.
            current_cursor: Current cursor value.

        Returns:
            True if pagination should continue, False otherwise.

        """
        if not items:
            return False
        return bool(next_cursor and next_cursor != current_cursor)

    async def _search_publications(
        self,
        query: str,
        limit: int | None = None,
        cursor: str = "*",
    ) -> AsyncIterator[dict[str, Any]]:
        """Search for publications using cursor-based pagination.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            cursor: Pagination cursor (* for first page).

        Yields:
            Publication records matching the query.

        """
        rows = min(limit, 100) if limit else 100
        fetched = 0

        try:
            while True:
                items, next_cursor = await self._fetch_search_page(query, rows, cursor)

                for item in items:
                    yield item
                    fetched += 1
                    if limit and fetched >= limit:
                        return

                if not self._should_continue_pagination(items, next_cursor, cursor):
                    break
                cursor = next_cursor  # type: ignore[assignment]

        except CrossRefApiError:
            raise
        except Exception as e:
            self.logger.error("crossref_search_failed", query=query, error=str(e))
            raise CrossRefApiError(f"CrossRef search failed: {e}") from e

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch CrossRef publications by DOI list (batch resolution).

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Must be 'work' or 'publication'.
            filter_ids: List of DOIs to resolve.
            filter_field: Field name (expected 'doi').
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each resolved publication.

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
            async for publication in self._fetch_batch_publications(batch):
                yield publication
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Multi-field filtering not supported by CrossRef API.

        CrossRef only supports single-field filtering by DOI.
        Use fetch_filtered() for DOI-based filtering instead.

        Raises:
            NotImplementedError: Always, as CrossRef doesn't support multi-field filtering.
        """
        # AsyncIterator requires yield before raise for proper generator creation
        if False:  # pragma: no cover
            yield {}  # Required for AsyncIterator type signature
        raise NotImplementedError(
            "CrossRef API does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )

    def _titles_match(
        self, query_title: str, found_title: str, threshold: float = 0.8
    ) -> bool:
        """Check if titles match (case-insensitive, normalized).

        Args:
            query_title: The title we're searching for.
            found_title: The title found in CrossRef.
            threshold: Unused, reserved for future fuzzy matching.

        Returns:
            True if titles match, False otherwise.
        """
        q = query_title.lower().strip()
        f = found_title.lower().strip()

        # Exact match
        if q == f:
            return True

        # Substring match (title may be truncated)
        if q in f or f in q:
            return True

        return False

    async def _search_by_title(
        self,
        title: str,
        limit: int = 3,
    ) -> dict[str, Any] | None:
        """Search for a publication by title.

        Args:
            title: Publication title to search for.
            limit: Maximum results to check for relevance.

        Returns:
            First relevant publication or None.
        """
        # Clean title for search (CrossRef limit)
        clean_title = title.strip()[:200]

        try:
            async for publication in self._search_publications(
                query=f'title:"{clean_title}"',
                limit=limit,
            ):
                # Check relevance (title must match)
                pub_titles = publication.get("title", [])
                found_title = pub_titles[0] if pub_titles else ""
                if self._titles_match(clean_title, found_title):
                    return publication
        except Exception as e:
            self.logger.debug(
                "crossref_title_search_failed",
                title=clean_title[:50],
                error=str(e),
            )

        return None

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with fallback search by title when DOI returns 404.

        Args:
            entity_type: Must be 'work' or 'publication'.
            filter_ids: List of DOIs to resolve.
            filter_field: Field name for filtering ('doi').
            fallback_mapping: Mapping {doi: title} for fallback search.
            limit: Maximum number of records to fetch.

        Yields:
            Publication records.
        """
        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"CrossRefAdapter supports 'work'/'publication', got: {entity_type}"
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0
        found_dois: set[str] = set()

        # Batch fetch (primary path)
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]

            async for publication in self._fetch_batch_publications(batch):
                doi = publication.get("DOI", "").lower()
                found_dois.add(doi)
                yield publication
                fetched += 1
                if limit and fetched >= limit:
                    return

        # Fallback for not-found DOIs
        for doi in dois:
            normalized_doi = (normalize_doi(doi) or "").lower()
            if normalized_doi in found_dois:
                continue

            title = fallback_mapping.get(doi) or fallback_mapping.get(normalized_doi)
            if not title:
                self.logger.debug("crossref_no_fallback_title", doi=doi)
                continue

            self.logger.info(
                "crossref_title_fallback_attempt",
                doi=doi,
                title=title[:50] + "..." if len(title) > 50 else title,
            )

            publication = await self._search_by_title(title)
            if publication:
                self.logger.info(
                    "crossref_title_fallback_success",
                    original_doi=doi,
                    found_doi=publication.get("DOI"),
                    title=title[:50],
                )
                yield publication
                fetched += 1
                if limit and fetched >= limit:
                    return
            else:
                self.logger.warning(
                    "crossref_title_fallback_not_found",
                    doi=doi,
                    title=title[:50],
                )

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch CrossRef publications.

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
            async for publication in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield publication
            return

        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"CrossRefAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if not query:
            raise ValueError(
                "CrossRef requires either filter_ids (DOIs) or query parameter"
            )

        async for publication in self._search_publications(query, limit):
            yield publication

    async def _probe_health(self) -> HealthStatus:
        """Probe CrossRef API health. Returns DEGRADED if response >5 sec."""
        try:
            url = f"{CROSSREF_API_BASE}/works"
            params = {
                "rows": "1",
                "mailto": self.mailto,
            }

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(
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

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for CrossRef.

        Returns:
            CrossRef works endpoint used for health probe.

        """
        return "/works"

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
