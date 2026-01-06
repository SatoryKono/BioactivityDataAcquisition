# src/bioetl/infrastructure/adapters/semanticscholar/adapter.py
"""Semantic Scholar API adapter for publication data extraction.

Implements FilterableDataSourcePort for batch DOI resolution with title fallback.
Uses POST /paper/batch for efficient batch DOI lookup.

Rate Limits:
- Without API key: Shared pool of 1000 req/sec (unstable)
- With API key: Guaranteed 1 req/sec per endpoint

Error Handling (RULES.md §3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

SEMANTICSCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Default fields to retrieve from Semantic Scholar
DEFAULT_FIELDS = (
    "paperId,externalIds,title,abstract,year,publicationDate,"
    "venue,authors,citationCount,referenceCount,isOpenAccess,"
    "openAccessPdf,tldr,fieldsOfStudy,publicationTypes,journal"
)


@dataclass
class SemanticScholarAdapter(BaseHttpAdapter):
    """Adapter for Semantic Scholar Academic Graph API.

    Implements FilterableDataSourcePort for:
    - fetch_filtered(): Batch DOI resolution via POST /paper/batch
    - fetch_filtered_with_fallback(): DOI lookup + title search fallback

    Rate Limit: 1 req/sec with API key (guaranteed).
    Retry: 429 → exponential backoff via UnifiedHTTPClient.

    Note: Batch response returns `null` for not-found IDs in the same order
    as the input array. This is used to identify DOIs requiring fallback.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        api_key: API key for stable rate limits (recommended).
        batch_size: Number of IDs per batch request (max 500, default 100).
        fields: Comma-separated list of fields to retrieve.
        metrics: Optional MetricsPort for recording adapter metrics.

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    api_key: str = ""
    batch_size: int = 100
    fields: str = DEFAULT_FIELDS
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="semanticscholar")
    """Provider identifier (required by DataSourcePort)."""

    def __post_init__(self) -> None:
        """Initialize adapter metrics."""
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with API key if available."""
        headers = {
            "User-Agent": "BioETL/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    # =========================================================================
    # DataSourcePort interface (basic fetch)
    # =========================================================================

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch publications via search (for incremental sync).

        Note: For batch DOI resolution use fetch_filtered().
        S2 uses offset-based pagination for search endpoint.

        Args:
            entity_type: Must be 'publication' or 'paper'.
            limit: Maximum number of records to fetch.
            query: Search query (optional, defaults to all papers).
            filter_ids: Optional list of IDs to filter by.
            filter_field: Optional field name for filtering.

        Yields:
            Dictionary records from Semantic Scholar API.

        """
        if filter_ids:
            effective_filter_field = filter_field or "doi"
            async for record in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield record
            return

        if entity_type not in ("publication", "paper"):
            raise ValueError(
                f"SemanticScholarAdapter supports 'publication' or 'paper', "
                f"got: {entity_type}"
            )

        offset = 0
        page_size = min(100, limit or 100)
        fetched = 0

        while True:
            params: dict[str, Any] = {
                "query": query or "*",
                "fields": self.fields,
                "offset": offset,
                "limit": page_size,
            }

            url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
            with self._adapter_metrics.measure_request("/paper/search"):
                response = await self.http_client.get_once(
                    url, params=params, headers=self._build_headers()
                )

            data = response.json()

            for record in data.get("data", []):
                if limit and fetched >= limit:
                    return
                yield record
                fetched += 1

            # Check if more results exist
            next_offset = data.get("next")
            if next_offset is None or (limit and fetched >= limit):
                return
            offset = next_offset

    # =========================================================================
    # FilterableDataSourcePort interface
    # =========================================================================

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Batch DOI resolution via Semantic Scholar POST /paper/batch.

        Args:
            entity_type: Must be 'publication' or 'paper'.
            filter_ids: List of DOIs to resolve.
            filter_field: Expected 'doi'.
            limit: Maximum records to return.

        Yields:
            Publication records from Semantic Scholar (excludes null/not-found).

        """
        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                expected="doi",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0

        # Process DOIs in batches
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]

            async for record in self._fetch_by_dois(batch):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with fallback to title search when DOI not found.

        Strategy:
        1. Batch DOI lookup via POST /paper/batch
        2. For null responses → search by title via GET /paper/search
        3. For empty DOIs (in filter_ids as "") → search by title only

        Args:
            entity_type: Must be 'publication' or 'paper'.
            filter_ids: List of DOIs (may include empty strings).
            filter_field: Expected 'doi'.
            fallback_mapping: Mapping {doi: title} for fallback search.
            limit: Maximum records to return.

        Yields:
            Publication records with `_lookup_method` field.

        """
        fetched = 0
        resolved_dois: set[str] = set()

        # Separate DOIs from title-only entries
        valid_dois = [d for d in filter_ids if d and d.strip()]
        title_only_entries = [d for d in filter_ids if not d or not d.strip()]

        # Phase 1: Batch DOI lookup
        for i in range(0, len(valid_dois), self.batch_size):
            batch = valid_dois[i : i + self.batch_size]

            # Batch returns results in same order, with null for not found
            batch_results = await self._fetch_batch_with_nulls(batch)

            for doi, record in zip(batch, batch_results, strict=True):
                if record is not None:
                    resolved_dois.add(doi.lower())
                    record["_lookup_method"] = "doi"
                    yield record
                    fetched += 1
                    if limit and fetched >= limit:
                        return

        # Phase 2: Fallback by title for unresolved DOIs
        unresolved_dois = [d for d in valid_dois if d.lower() not in resolved_dois]

        for doi in unresolved_dois:
            if limit and fetched >= limit:
                return

            title = fallback_mapping.get(doi)
            if not title:
                self.logger.warning(
                    "no_fallback_title",
                    doi=doi,
                )
                continue

            async for record in self._search_by_title(title):
                record["_lookup_method"] = "title_fallback"
                record["_original_doi"] = doi
                yield record
                fetched += 1
                break  # Take first match only

        # Phase 3: Title-only entries (empty DOIs)
        for empty_doi in title_only_entries:
            if limit and fetched >= limit:
                return

            title = fallback_mapping.get(empty_doi, fallback_mapping.get(""))
            if not title:
                continue

            async for record in self._search_by_title(title):
                record["_lookup_method"] = "title_only"
                yield record
                fetched += 1
                break

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Multi-field filtering - not implemented for Semantic Scholar.

        Use fetch_filtered() for DOI-based filtering.

        Raises:
            NotImplementedError: Always, as S2 doesn't support multi-field filtering.

        """
        if False:  # pragma: no cover
            yield {}
        raise NotImplementedError(
            "Semantic Scholar adapter supports only DOI filtering. "
            "Use fetch_filtered() or fetch_filtered_with_fallback()."
        )

    # =========================================================================
    # Internal methods
    # =========================================================================

    async def _fetch_by_dois(
        self,
        dois: list[str],
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch publications by batch of DOIs.

        Uses POST /paper/batch with `ids: ["DOI:..."]`.
        Filters out null (not found) results.

        Args:
            dois: List of DOIs to resolve.

        Yields:
            Publication records (excludes null/not-found).

        """
        if not dois:
            return

        results = await self._fetch_batch_with_nulls(dois)

        for record in results:
            if record is not None:
                yield record

    async def _fetch_batch_with_nulls(
        self,
        dois: list[str],
    ) -> list[dict[str, Any] | None]:
        """Fetch batch preserving null positions for not-found tracking.

        Returns list of same length as input, with None for not-found DOIs.

        Args:
            dois: List of DOIs to resolve.

        Returns:
            List of records (or None for not-found) in same order as input.

        """
        if not dois:
            return []

        # Format DOIs with prefix
        formatted_ids = [f"DOI:{self._normalize_doi(d)}" for d in dois if d]

        return await self._fetch_batch_raw(formatted_ids)

    async def _fetch_batch_raw(
        self,
        paper_ids: list[str],
    ) -> list[dict[str, Any] | None]:
        """Execute batch request and return raw response array.

        Semantic Scholar returns array in same order as input,
        with null for not-found papers.

        Args:
            paper_ids: List of paper IDs with prefixes (e.g., "DOI:10.1038/...").

        Returns:
            List of records (or None) in same order as input.

        """
        self.logger.debug(
            "semanticscholar_batch_request",
            paper_count=len(paper_ids),
        )

        # Include fields in URL query string
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/batch?fields={self.fields}"
        json_body = {"ids": paper_ids}

        with self._adapter_metrics.measure_request("/paper/batch"):
            response = await self.http_client.post(
                url,
                json=json_body,
                headers=self._build_headers(),
            )

        # Response is JSON array
        result: list[dict[str, Any] | None] = response.json()
        return result

    async def _search_by_title(
        self,
        title: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Search publications by title (fuzzy match).

        Uses GET /paper/search with query for best title match.

        Args:
            title: Publication title to search for.

        Yields:
            Publication records matching the title.

        """
        # Clean title for search
        cleaned_title = self._escape_title_for_search(title)

        params: dict[str, Any] = {
            "query": cleaned_title,
            "fields": self.fields,
            "limit": 5,  # Return top matches
        }

        self.logger.debug(
            "semanticscholar_title_search",
            title=title[:100],
        )

        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
        with self._adapter_metrics.measure_request("/paper/search"):
            response = await self.http_client.get_once(
                url, params=params, headers=self._build_headers()
            )

        data = response.json()

        for record in data.get("data", []):
            yield record

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI by removing URL prefix."""
        if doi.startswith("https://doi.org/"):
            return doi[16:]
        if doi.startswith("http://doi.org/"):
            return doi[15:]
        if doi.startswith("doi:"):
            return doi[4:]
        if doi.startswith("DOI:"):
            return doi[4:]
        return doi

    @staticmethod
    def _escape_title_for_search(title: str) -> str:
        """Escape title for Semantic Scholar search query."""
        # Remove special characters that might break the query
        cleaned = title.replace('"', " ").replace("'", " ")
        # Normalize whitespace
        return " ".join(cleaned.split())

    async def _probe_health(self) -> HealthStatus:
        """Probe Semantic Scholar API health.

        Returns DEGRADED if response time exceeds 5 seconds.

        Returns:
            HealthStatus indicating API availability.

        """
        try:
            url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
            params = {
                "query": "test",
                "limit": 1,
                "fields": "paperId",
            }

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(
                    url, params=params, headers=self._build_headers()
                )
            elapsed = time.monotonic() - start_time

            if response.status_code != 200:
                self.logger.warning(
                    "semanticscholar_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            # Slow response = degraded
            if elapsed > 5.0:
                self.logger.warning(
                    "semanticscholar_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY

        except Exception as e:
            self.logger.warning(
                "semanticscholar_health_check_failed",
                error=str(e),
            )
            raise  # Let health_check() return _fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get fallback health status on probe failure.

        Returns:
            HealthStatus.UNHEALTHY on probe failure.

        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint.

        Returns:
            Search endpoint used for health probe.

        """
        return "/paper/search"

    async def aclose(self) -> None:
        """Close adapter resources.

        Safely closes HTTP client via context manager interface.
        Idempotent - safe to call multiple times.
        """
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)
