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

__all__ = ["OPENALEX_API_BASE", "OPENALEX_RUNTIME_ERRORS", "OpenAlexAdapter"]


import contextlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
)
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)
from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler
from bioetl.infrastructure.adapters.openalex.health_probe import probe_openalex_health
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_doi_filter_params,
    build_openalex_search_params,
    build_openalex_title_search_params,
)
from bioetl.infrastructure.adapters.openalex.response_parser import (
    parse_openalex_next_cursor,
    parse_openalex_results,
)

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
class OpenAlexAdapter(OpenAlexAdapterHelpersMixin, BaseHttpAdapter):
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
    title_search_cache_size: int = 256

    provider_name: str = field(init=False, default="openalex")
    """Provider identifier (required by DataSourcePort)."""
    _title_search_cache: dict[tuple[str, int], list[BronzeRecord]] = field(
        init=False, default_factory=dict
    )
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize adapter metrics and helper components."""
        self._init_adapter_metrics()
        self._fallback_fetch_service = FallbackFetchOrchestratorService(
            self._adapter_metrics
        )

        # Initialize helper components for fallback handling
        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_by_title,
        )

    @staticmethod
    def _is_supported_entity_type(entity_type: str) -> bool:
        return entity_type in ("work", "publication")

    def _validate_entity_type(self, entity_type: str) -> None:
        if self._is_supported_entity_type(entity_type):
            return
        raise ValueError(
            f"OpenAlexAdapter supports 'work' or 'publication', got: {entity_type}"
        )

    async def _request_works_payload(
        self,
        params: dict[str, str],
    ) -> dict[str, Any]:  # Any: untyped OpenAlex API payload
        """Execute OpenAlex `/works` request and return decoded payload."""
        url = f"{OPENALEX_API_BASE}/works"
        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/works"):
            response = await self.http_client.get(
                url, params=params, headers=self._build_headers()
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {}

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch OpenAlex records by DOI or title."""
        self._validate_entity_type(entity_type)

        if filter_field == "doi":
            async for work in self._fetch_filtered_by_doi(filter_ids, limit):
                yield work
            return
        if filter_field == "title":
            async for work in self._fetch_filtered_by_title(filter_ids, limit):
                yield work
            return

        self.logger.warning(
            "unsupported_filter_field",
            field=filter_field,
            msg="OpenAlex only supports 'doi' or 'title' filtering, skipping",
        )

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
        """Fetch works by title search."""
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
                result = dict(results[0])
                result["_lookup_method"] = "title"
                result["_original_id"] = title
                result["_search_title"] = title
                yield result
                found += 1
                fetched += 1

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
        limit: int | None,
        start_count: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 batch DOI lookup."""
        count = start_count
        for i in range(0, len(valid_dois), self.batch_size):
            if limit and count >= limit:
                return

            batch = valid_dois[i : i + self.batch_size]
            async for work in self._fetch_by_dois(batch):
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
        """Fetch DOI-first records with title fallback resolution."""
        if not self._is_supported_entity_type(entity_type):
            raise ValueError(
                f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
            )
        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field_for_fallback",
                field=filter_field,
                msg="OpenAlex fallback only supports 'doi' filtering, skipping",
            )
            return

        def _log_phase1_summary(total: int, found: int) -> None:
            self.logger.info(
                "openalex_doi_lookup_summary",
                total_dois=total,
                found_by_doi=found,
                missing_dois=total - found,
                hit_rate_pct=round(found / total * 100, 1) if total else 0.0,
            )

        def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            return self._batch_doi_lookup(primary_ids, request_limit, 0)

        request = FallbackFetchRequest(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            normalize_id=self._normalize_doi,
            extract_record_id=self._extract_doi_from_record,
            fallback_handler=self._fallback_handler,
            limit=limit,
            primary_lookup_method="doi",
            phase1_summary_logger=_log_phase1_summary,
        )
        async for work in self._fallback_fetch_service.execute(request):
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
        """Fetch OpenAlex works by filters or free-text query."""
        if filter_ids:
            effective_filter_field = filter_field or "doi"
            async for work in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield work
            return

        self._validate_entity_type(entity_type)
        if not query:
            raise ValueError(
                "OpenAlex requires either filter_ids (DOIs) or query parameter"
            )

        async for work in self._fetch_by_query(query=query, limit=limit):
            yield work

    # =========================================================================
    # Internal methods
    # =========================================================================

    async def _fetch_by_query(
        self,
        *,
        query: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works with cursor pagination for free-text query."""
        fetched = 0
        cursor: str | None = "*"
        per_page = min(self.batch_size, 200)

        while cursor:
            params = build_openalex_search_params(
                mailto=self.mailto,
                query=query,
                cursor=cursor,
                per_page=per_page,
            )
            payload = await self._request_works_payload(params)
            results = parse_openalex_results(payload)

            for work in results:
                if limit and fetched >= limit:
                    return
                yield work
                fetched += 1

            cursor = parse_openalex_next_cursor(payload)

    async def _fetch_by_dois(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Fetch works by batch DOI filter."""
        if not dois:
            return

        normalized_raw = [self._normalize_doi(d) for d in dois if d]
        normalized: list[str] = [d for d in normalized_raw if d is not None]
        if not normalized:
            return

        params = build_openalex_doi_filter_params(
            mailto=self.mailto,
            dois=normalized,
        )
        self.logger.debug(
            "openalex_batch_doi_request",
            doi_count=len(normalized),
        )
        payload = await self._request_works_payload(params)
        results = parse_openalex_results(payload)

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
        """Search works by title with in-memory cache."""
        normalized_title = title.strip()
        cache_key = (normalized_title.casefold(), limit)
        cached = self._title_search_cache.get(cache_key)
        if cached is not None:
            return [dict(result) for result in cached]

        clean_title = self._escape_title_for_search(normalized_title[:200])
        params = build_openalex_title_search_params(
            mailto=self.mailto,
            escaped_title=clean_title,
            limit=limit,
        )
        self.logger.debug(
            "openalex_title_search",
            title=title[:50],
        )

        try:
            payload = await self._request_works_payload(params)
            results = parse_openalex_results(payload)
            cached_results = [dict(result) for result in results]
            self._title_search_cache[cache_key] = cached_results
            if len(self._title_search_cache) > self.title_search_cache_size:
                oldest_key = next(iter(self._title_search_cache))
                del self._title_search_cache[oldest_key]
            return [dict(result) for result in cached_results]

        except OPENALEX_RUNTIME_ERRORS as e:
            self.logger.debug(
                "openalex_title_search_failed",
                title=title[:50],
                error=str(e),
            )
            self._title_search_cache[cache_key] = []
            return []

    async def _probe_health(self) -> HealthStatus:
        """Probe OpenAlex API health."""
        try:
            return await probe_openalex_health(
                api_base=OPENALEX_API_BASE,
                mailto=self.mailto,
                http_client=self.http_client,
                logger=self.logger,
                adapter_metrics=self._adapter_metrics,
                headers=self._build_headers(),
            )
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
