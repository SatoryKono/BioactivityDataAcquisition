"""OpenAlex data source adapter.

Implements FilterableDataSourcePort for OpenAlex Works API.
See RULES.md Appendix A for rate limits and retry strategy.

Uses httpx via UnifiedHTTPClient for REST/JSON API access.

Error Handling (RULES.md S3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Polite Pool:
- OpenAlex provides higher rate limits (10 req/sec) when `mailto` is provided
- Always send mailto in query parameters
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.openalex.client_helpers_mixin import (
    _OpenAlexAdapterHelpersMixin,
)
from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

OPENALEX_API_BASE = "https://api.openalex.org"

OPENALEX_RUNTIME_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    Exception,
)


@dataclass
class OpenAlexAdapter(_OpenAlexAdapterHelpersMixin, BaseHttpAdapter):
    """OpenAlex data source adapter.

    Inherits from BaseHttpAdapter for standardized lifecycle management
    and Template Method pattern for health checks.

    Implements DataSourcePort and FilterableDataSourcePort for OpenAlex
    Works API with batch DOI resolution and title fallback support.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        mailto: Technical email for polite pool access (required).
            OpenAlex provides higher rate limits (10 req/sec) with mailto.
            See: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
        batch_size: Number of DOIs per batch request (max 50 recommended).
        metrics: Optional MetricsPort for recording adapter metrics.

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    mailto: str
    batch_size: int = 50
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="openalex")
    """Provider identifier (required by DataSourcePort)."""

    def __post_init__(self) -> None:
        """Initialize adapter metrics and helper components."""
        self._init_adapter_metrics()

        # Initialize helper components for fallback handling
        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_by_title,
        )

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by DOI or title.

        Implements FilterableDataSourcePort.fetch_filtered().

        For DOIs: Uses `filter=doi:id1|id2|id3` for efficient batch lookup.
        For titles: Uses individual title.search queries with rate limiting.

        Args:
            entity_type: Must be 'work' or 'publication'.
            filter_ids: List of DOIs or titles to resolve.
            filter_field: Field name ('doi' or 'title').
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each resolved publication.

        Raises:
            ValueError: If entity_type is not 'work' or 'publication'.

        Returns:
            Async iterator yielding fetched records.
        """
        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if filter_field == "doi":
            # Batch DOI lookup (existing logic)
            async for work in self._fetch_filtered_by_doi(filter_ids, limit):
                yield work
        elif filter_field == "title":
            # Title search with rate limiting
            async for work in self._fetch_filtered_by_title(filter_ids, limit):
                yield work
        else:
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                msg="OpenAlex only supports 'doi' or 'title' filtering, skipping",
            )
            # Return empty - don't try to use unsupported field as DOI
            return

    async def _fetch_filtered_by_doi(
        self,
        filter_ids: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by DOI list (batch resolution).

        Uses `filter=doi:id1|id2|id3` for efficient batch lookup.

        Args:
            filter_ids: List of DOIs to resolve.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each resolved publication.
        """
        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0

        # Process DOIs in batches (max 50 recommended per request)
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]
            async for work in self._fetch_by_dois(batch):
                work["_lookup_method"] = "doi"
                yield work
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def _fetch_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works by title search.

        Uses individual title.search queries with rate limiting.
        Rate limit: 100ms delay between requests (10 req/sec).

        Args:
            titles: List of publication titles to search.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each found publication.
        """
        self.logger.info(
            "openalex_title_search_start",
            total_titles=len(titles),
            limit=limit,
        )

        effective_titles = titles[:limit] if limit else titles
        fetched = 0
        found = 0

        for title in effective_titles:
            if limit and fetched >= limit:
                break

            # Skip empty titles
            if not title or not title.strip():
                continue

            results = await self._search_by_title(title, limit=1)
            if results:
                result = results[0]
                result["_lookup_method"] = "title"
                result["_original_id"] = title
                result["_search_title"] = title  # Track which title matched
                yield result
                found += 1
                fetched += 1

            # Rate limiting: 100ms delay between requests (10 req/sec)
            await asyncio.sleep(0.1)

        # Log summary statistics
        self.logger.info(
            "openalex_title_lookup_summary",
            total_titles=len(effective_titles),
            found_by_title=found,
            hit_rate_pct=round(found / len(effective_titles) * 100, 1)
            if effective_titles
            else 0.0,
        )

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering not supported by OpenAlex.

        OpenAlex supports DOI filtering via fetch_filtered().
        For other filters, use the general search API.

        Raises:
            NotImplementedError: Always, as OpenAlex doesn't support multi-field filtering.

        Args:
            entity_type: Entity type identifier.
            filters: Filters.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
        raise NotImplementedError(
            "OpenAlex adapter does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )
        yield {}  # pragma: no cover - keeps AsyncIterator contract

    async def _batch_doi_lookup(
        self,
        valid_dois: list[str],
        found_dois: set[str],
        limit: int | None,
        start_count: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase 1: Batch DOI lookup for valid DOIs.

        Args:
            valid_dois: List of valid DOIs to lookup.
            found_dois: Set to track found DOIs (mutated).
            limit: Maximum records to fetch.
            start_count: Number of records already fetched.

        Yields:
            Work records with _lookup_method field.
        """
        count = start_count
        for i in range(0, len(valid_dois), self.batch_size):
            if limit and count >= limit:
                return

            batch = valid_dois[i : i + self.batch_size]
            async for work in self._fetch_by_dois(batch):
                doi = self._extract_doi_from_record(work)
                if doi:
                    found_dois.add(doi.lower())
                work["_lookup_method"] = "doi"
                count += 1
                yield work
                if limit and count >= limit:
                    return

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch with fallback search by title when DOI not found.

        Strategy:
        1. Try batch DOI lookup for valid DOIs
        2. For DOIs not found -> search by title from fallback_mapping
        3. For empty DOIs (in filter_ids as "") -> search by title only

        Args:
            entity_type: Must be 'work' or 'publication'.
            filter_ids: List of DOIs to resolve (may include empty strings).
            filter_field: Field name for filtering ('doi').
            fallback_mapping: Mapping {doi: title} for fallback search.
            limit: Maximum number of records to fetch.

        Yields:
            Work records with `_lookup_method` field indicating resolution method.

        Returns:
            Async iterator yielding fetched records.
        """
        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
            )

        # Validate filter_field - fallback only supports DOI-based lookups
        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field_for_fallback",
                field=filter_field,
                msg="OpenAlex fallback only supports 'doi' filtering, skipping",
            )
            return

        fetched = 0
        found_dois: set[str] = set()

        # Separate DOIs from title-only markers (__title_only_N__ format)
        valid_dois = [
            d
            for d in filter_ids
            if d and d.strip() and not d.startswith("__title_only_")
        ]
        title_only_entries = [
            d
            for d in filter_ids
            if not d or not d.strip() or d.startswith("__title_only_")
        ]

        # Phase 1: Batch DOI lookup
        async for work in self._batch_doi_lookup(
            valid_dois, found_dois, limit, fetched
        ):
            yield work
            fetched += 1
            if limit and fetched >= limit:
                return

        # Log Phase 1 summary
        if valid_dois:
            self.logger.info(
                "openalex_doi_lookup_summary",
                total_dois=len(valid_dois),
                found_by_doi=len(found_dois),
                missing_dois=len(valid_dois) - len(found_dois),
                hit_rate_pct=round(len(found_dois) / len(valid_dois) * 100, 1),
            )

        # Phase 2: Fallback by title for unresolved DOIs
        async for work in self._fallback_handler.process_missing_dois(
            dois=valid_dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=self._normalize_doi,
            limit=limit,
            fetched=fetched,
        ):
            yield work
            fetched += 1
            if limit and fetched >= limit:
                return

        # Phase 3: Title-only entries (using handler)
        async for work in self._fallback_handler.process_title_only_entries(
            entries=title_only_entries,
            fallback_mapping=fallback_mapping,
            limit=limit,
            fetched=fetched,
        ):
            yield work

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex works.

        Implements DataSourcePort.fetch().

        Args:
            entity_type: Must be 'work' or 'publication'.
            limit: Maximum number of records to fetch.
            query: Search query for OpenAlex (optional).
            filter_ids: List of DOIs to resolve (optional).
            filter_field: Field name for filtering (expected 'doi').

        Yields:
            Dictionary records from OpenAlex API.

        Raises:
            ValueError: If entity_type is invalid or no query/filter_ids provided.

        Returns:
            Async iterator yielding fetched records.
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
                f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if not query:
            raise ValueError(
                "OpenAlex requires either filter_ids (DOIs) or query parameter"
            )

        # Search by query using cursor pagination
        fetched = 0
        cursor = "*"

        while cursor:
            params = self._build_base_params()
            params.update(
                {
                    "search": query,
                    "cursor": cursor,
                    "per-page": str(min(self.batch_size, 200)),
                }
            )

            url = f"{OPENALEX_API_BASE}/works"
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/works"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            data = response.json()
            results = data.get("results", [])

            for work in results:
                if limit and fetched >= limit:
                    return
                yield work
                fetched += 1

            # Get next cursor for pagination
            cursor = data.get("meta", {}).get("next_cursor")

    # =========================================================================
    # Internal methods
    # =========================================================================

    async def _fetch_by_dois(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Fetch works by batch of DOIs.

        Uses `filter=doi:doi1|doi2|doi3` syntax for efficient batch lookup.
        """
        if not dois:
            return

        # Normalize DOIs (remove https://doi.org/ prefix if present)
        normalized_raw = [self._normalize_doi(d) for d in dois if d]
        normalized: list[str] = [d for d in normalized_raw if d is not None]

        if not normalized:
            return

        # Build filter with OR operator (pipe-separated)
        doi_filter = "|".join(normalized)

        params = self._build_base_params()
        params.update(
            {
                "filter": f"doi:{doi_filter}",
                "per-page": str(len(normalized)),
            }
        )

        self.logger.debug(
            "openalex_batch_doi_request",
            doi_count=len(normalized),
        )

        url = f"{OPENALEX_API_BASE}/works"
        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/works"):
            response = await self.http_client.get(
                url, params=params, headers=self._build_headers()
            )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record request for metadata enrichment
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)

        data = response.json()
        results = data.get("results", [])

        # Log hit rate for diagnostics
        if len(results) < len(normalized):
            self.logger.info(
                "openalex_batch_partial_results",
                requested=len(normalized),
                found=len(results),
                hit_rate=round(len(results) / len(normalized) * 100, 1),
            )

        for work in results:
            yield work

    async def _search_by_title(self, title: str, limit: int = 3) -> list[BronzeRecord]:
        """Search works by title (fuzzy match).

        Uses `filter=title.search:...` syntax.

        Args:
            title: Publication title to search for.
            limit: Maximum results to check for relevance.

        Returns:
            List of relevant publications (empty if none found).
        """
        # Clean title for search
        clean_title = self._escape_title_for_search(title.strip()[:200])

        params = self._build_base_params()
        params.update(
            {
                "filter": f"title.search:{clean_title}",
                "per-page": str(limit),
            }
        )

        self.logger.debug(
            "openalex_title_search",
            title=title[:50],
        )

        try:
            url = f"{OPENALEX_API_BASE}/works"
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/works"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            data = response.json()
            results: list[BronzeRecord] = data.get(
                "results", []
            )  # Any: untyped OpenAlex API JSON response
            return results

        except OPENALEX_RUNTIME_ERRORS as e:
            self.logger.debug(
                "openalex_title_search_failed",
                title=title[:50],
                error=str(e),
            )
            return []

    async def _probe_health(self) -> HealthStatus:
        """Probe OpenAlex API health. Returns DEGRADED if response >5 sec."""
        try:
            url = f"{OPENALEX_API_BASE}/works"
            params = {
                "per-page": "1",
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
                    "openalex_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            # Slow response = degraded
            if elapsed > 5.0:
                self.logger.warning(
                    "openalex_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY

        except OPENALEX_RUNTIME_ERRORS as e:
            self.logger.warning(
                "openalex_health_check_failed",
                error=str(e),
            )
            raise  # Let health_check() return _fallback_health_status()

    async def aclose(self) -> None:
        """Close adapter resources.

        Overrides BaseHttpAdapter.aclose() to properly close the HTTP client.
        Safely closes via the public context manager interface.
        Idempotent - safe to call multiple times.
        """
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


def _create_openalex_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adap...
) -> OpenAlexAdapter:
    """Custom creator for OpenAlex adapter.

    Handles logic for obtaining mailto from settings.

    Args:
        http_client: HTTP client
        logger: Logger
        settings: Application settings
        **kwargs: Additional parameters (mailto, batch_size, metrics)

    Returns:
        Initialized OpenAlexAdapter

    Raises:
        ValueError: If mailto is not provided and not found in settings

    """
    # Mailto: from kwargs or settings
    mailto = kwargs.get("mailto")
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "OpenAlex adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )

    if http_client is None:
        raise ValueError("OpenAlex adapter requires http_client")
    if logger is None:
        raise ValueError("OpenAlex adapter requires logger")

    return OpenAlexAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
    )
