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

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

OPENALEX_API_BASE = "https://api.openalex.org"


@dataclass
class OpenAlexAdapter(BaseHttpAdapter):
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
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

        # Initialize helper components for fallback handling
        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_by_title,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers for OpenAlex API."""
        return {
            "User-Agent": f"BioETL/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

    def _build_base_params(self) -> dict[str, str]:
        """Build base query parameters with mailto for polite pool."""
        return {"mailto": self.mailto}

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch OpenAlex works by DOI list (batch resolution).

        Implements FilterableDataSourcePort.fetch_filtered().

        Uses `filter=doi:id1|id2|id3` for efficient batch lookup.

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
                f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
            )

        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                msg="OpenAlex only supports DOI filtering, assuming DOIs",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0

        # Process DOIs in batches (max 50 recommended per request)
        for i in range(0, len(dois), self.batch_size):
            batch = dois[i : i + self.batch_size]
            async for work in self._fetch_by_dois(batch):
                yield work
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Multi-field filtering not supported by OpenAlex.

        OpenAlex supports DOI filtering via fetch_filtered().
        For other filters, use the general search API.

        Raises:
            NotImplementedError: Always, as OpenAlex doesn't support multi-field filtering.
        """
        # AsyncIterator requires yield before raise for proper generator creation
        if False:  # pragma: no cover
            yield {}  # Required for AsyncIterator type signature
        raise NotImplementedError(
            "OpenAlex adapter does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
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
        """
        if entity_type not in ("work", "publication"):
            raise ValueError(
                f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
            )

        fetched = 0
        found_dois: set[str] = set()

        # Separate valid DOIs from title-only entries
        valid_dois = [d for d in filter_ids if d and d.strip()]
        title_only_entries = [d for d in filter_ids if not d or not d.strip()]

        # Phase 1: Batch DOI lookup for valid DOIs
        for i in range(0, len(valid_dois), self.batch_size):
            if limit and fetched >= limit:
                return

            batch = valid_dois[i : i + self.batch_size]
            async for work in self._fetch_by_dois(batch):
                doi = self._extract_doi_from_record(work)
                if doi:
                    found_dois.add(doi.lower())
                work["_lookup_method"] = "doi"
                yield work
                fetched += 1
                if limit and fetched >= limit:
                    return

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

        # Phase 3: Title-only entries (empty DOIs)
        for empty_doi in title_only_entries:
            if limit and fetched >= limit:
                return

            # Get title from fallback_mapping (may use "" as key for empty DOIs)
            title = fallback_mapping.get(empty_doi, fallback_mapping.get(""))
            if not title:
                continue

            self.logger.info(
                "openalex_title_only_search",
                title=title[:50],
            )

            found_work = await self._search_by_title(title, limit=1)
            if found_work:
                found_work["_lookup_method"] = "title_only"
                yield found_work
                fetched += 1

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
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
            with self._adapter_metrics.measure_request("/works"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )

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

    async def _fetch_by_dois(self, dois: list[str]) -> AsyncIterator[dict[str, Any]]:
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
        with self._adapter_metrics.measure_request("/works"):
            response = await self.http_client.get(
                url, params=params, headers=self._build_headers()
            )

        data = response.json()

        for work in data.get("results", []):
            yield work

    async def _search_by_title(
        self, title: str, limit: int = 3
    ) -> dict[str, Any] | None:
        """Search works by title (fuzzy match).

        Uses `filter=title.search:...` syntax.

        Args:
            title: Publication title to search for.
            limit: Maximum results to check for relevance.

        Returns:
            First relevant publication or None.
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
            with self._adapter_metrics.measure_request("/works"):
                response = await self.http_client.get(
                    url, params=params, headers=self._build_headers()
                )

            data = response.json()
            results: list[dict[str, Any]] = data.get("results", [])

            if results:
                first_result: dict[str, Any] = results[0]
                return first_result
            return None

        except Exception as e:
            self.logger.debug(
                "openalex_title_search_failed",
                title=title[:50],
                error=str(e),
            )
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str | None:
        """Normalize DOI by removing URL prefix."""
        if not doi:
            return None
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            return doi[16:]
        if doi.startswith("http://doi.org/"):
            return doi[15:]
        if doi.startswith("doi:"):
            return doi[4:]
        return doi

    @staticmethod
    def _escape_title_for_search(title: str) -> str:
        """Escape title for OpenAlex title.search filter.

        OpenAlex uses + for spaces in search queries.
        Special characters that break the filter are removed.
        """
        # Remove special characters that break the filter
        cleaned = title.replace(":", " ").replace("|", " ").replace(",", " ")
        # Replace spaces with + for search
        return "+".join(cleaned.split())

    @staticmethod
    def _extract_doi_from_record(record: dict[str, Any]) -> str | None:
        """Extract normalized DOI from OpenAlex record."""
        doi_url: str = record.get("doi", "") or ""
        if not doi_url:
            return None
        if doi_url.startswith("https://doi.org/"):
            extracted: str = doi_url[16:].lower()
            return extracted
        lowered: str = doi_url.lower()
        return lowered

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

        except Exception as e:
            self.logger.warning(
                "openalex_health_check_failed",
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
        """Get the health check endpoint for OpenAlex.

        Returns:
            OpenAlex works endpoint used for health probe.

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


def _create_openalex_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,
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
