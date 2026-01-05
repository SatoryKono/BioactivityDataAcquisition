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
from bioetl.infrastructure.adapters.crossref.batch import (
    DoiBatchProcessor,
    SearchPaginator,
)
from bioetl.infrastructure.adapters.crossref.fallback import TitleFallbackHandler

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
        """Initialize adapter metrics and helper components."""
        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

        # Initialize helper components for batch fetching and search
        self._batch_fetcher = DoiBatchProcessor(
            http=self.http_client,
            logger=self.logger,
            metrics=self._adapter_metrics,
            mailto=self.mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=self._build_headers,
        )
        self._search_paginator = SearchPaginator(
            http=self.http_client,
            logger=self.logger,
            metrics=self._adapter_metrics,
            mailto=self.mailto,
            api_base=CROSSREF_API_BASE,
            headers_fn=self._build_headers,
        )
        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_paginator.search,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with polite pool identification."""
        return {
            "User-Agent": f"BioETL/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

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
            async for publication in self._batch_fetcher.fetch_batch(batch):
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
            async for publication in self._batch_fetcher.fetch_batch(batch):
                doi = publication.get("DOI", "").lower()
                found_dois.add(doi)
                yield publication
                fetched += 1
                if limit and fetched >= limit:
                    return

        # Fallback for not-found DOIs using handler
        async for pub in self._fallback_handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=normalize_doi,
            limit=limit,
            fetched=fetched,
        ):
            yield pub

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

        async for publication in self._search_paginator.search(query, limit):
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
