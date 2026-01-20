# src/bioetl/infrastructure/adapters/semanticscholar/adapter.py
"""Semantic Scholar API adapter for publication data extraction.

Implements FilterableDataSourcePort for batch DOI resolution with title fallback.
Uses POST /paper/batch for efficient batch DOI lookup.

Supports three-phase fallback strategy:
- Phase 1: Batch DOI lookup via POST /paper/batch
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs

Rate Limits:
- Without API key: Shared pool of 1000 req/sec (unstable)
- With API key: Guaranteed 1 req/sec per endpoint

Error Handling (RULES.md §3.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.ports import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
)

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

    _request_collector: APIRequestCollector = field(
        init=False, default_factory=APIRequestCollector
    )
    """Collects API request metadata for Bronze layer enrichment."""

    def __post_init__(self) -> None:
        """Initialize adapter metrics and helper components."""
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

        # Initialize helper component for fallback handling
        self._fallback_handler = SemanticScholarTitleFallbackHandler(
            http_client=self.http_client,
            logger=self.logger,
            metrics=self._adapter_metrics,
            api_key=self.api_key,
            fields=self.fields,
        )

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
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/paper/search"):
                response = await self.http_client.get_once(
                    url, params=params, headers=self._build_headers()
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

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
                record["_lookup_method"] = "doi"
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def _batch_doi_phase(
        self,
        valid_dois: list[str],
        resolved_dois: set[str],
        limit: int | None,
        start_count: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Phase 1: Batch DOI lookup via POST /paper/batch.

        Args:
            valid_dois: List of valid DOIs to lookup.
            resolved_dois: Set to track resolved DOIs (mutated).
            limit: Maximum records to fetch.
            start_count: Number of records already fetched.

        Yields:
            Publication records with _lookup_method field.
        """
        count = start_count
        for i in range(0, len(valid_dois), self.batch_size):
            if limit and count >= limit:
                return

            batch = valid_dois[i : i + self.batch_size]
            batch_results = await self._fetch_batch_with_nulls(batch)

            for doi, record in zip(batch, batch_results, strict=True):
                if record is not None:
                    resolved_dois.add(doi.lower())
                    record["_lookup_method"] = "doi"
                    count += 1
                    yield record
                    if limit and count >= limit:
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

        Strategy (three-phase fallback):
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

        valid_dois = [d for d in filter_ids if d and d.strip()]
        title_only_entries = [d for d in filter_ids if not d or not d.strip()]

        # Phase 1: Batch DOI lookup
        async for record in self._batch_doi_phase(
            valid_dois, resolved_dois, limit, fetched
        ):
            yield record
            fetched += 1
            if limit and fetched >= limit:
                return

        # Phase 2: Fallback by title for unresolved DOIs (using handler)
        async for record in self._fallback_handler.process_missing_dois(
            dois=valid_dois,
            found_dois=resolved_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,  # DOIs already normalized
            limit=limit,
            fetched=fetched,
        ):
            yield record
            fetched += 1
            if limit and fetched >= limit:
                return

        # Phase 3: Title-only entries (using handler)
        async for record in self._fallback_handler.process_title_only_entries(
            entries=title_only_entries,
            fallback_mapping=fallback_mapping,
            limit=limit,
            fetched=fetched,
        ):
            yield record

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

        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/paper/batch"):
            response = await self.http_client.post(
                url,
                json=json_body,
                headers=self._build_headers(),
            )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record request for metadata enrichment
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)

        # Response is JSON array
        result: list[dict[str, Any] | None] = response.json()
        return result

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

    async def _probe_health(self) -> HealthStatus:
        """Probe Semantic Scholar API health.

        Returns DEGRADED if response time exceeds 5 seconds or rate limited (429).
        Without API key, 429 is expected and should not fail the pipeline.

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

            # Rate limited (429) - return DEGRADED instead of UNHEALTHY
            # Without API key, rate limiting is expected behavior
            if response.status_code == 429:
                self.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    message="Rate limited (429). Consider using API key for stable access.",
                )
                return HealthStatus.DEGRADED

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
            # Check if it's a 429 error from httpx
            error_str = str(e)
            if "429" in error_str:
                self.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    message="Rate limited (429). Consider using API key.",
                )
                return HealthStatus.DEGRADED
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

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Returns aggregated metadata from all API requests made since last clear.
        Used by BatchExecutor to enrich Bronze layer metadata.

        Args:
            api_version: Optional API version string.

        Returns:
            SourceMetadata with request details and statistics.
        """
        metadata = self._request_collector.to_source_metadata(
            source_type="api",
            url=SEMANTICSCHOLAR_BASE_URL,
            api_version=api_version or "v1",
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

    async def aclose(self) -> None:
        """Close adapter resources.

        Safely closes HTTP client via context manager interface.
        Idempotent - safe to call multiple times.
        """
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)
