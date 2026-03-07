"""CrossRef adapter facade for DataSourcePort and FilterableDataSourcePort."""

from __future__ import annotations

__all__ = [
    "CROSSREF_API_BASE",
    "CROSSREF_HEALTH_ERRORS",
    "CrossRefAdapter",
    "CrossRefFetchFlow",
    "CrossRefQueryBuilder",
    "CrossRefResponseMapper",
]

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.normalization import normalize_doi
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    DefaultFallbackExecutionStrategy,
    FallbackFetchOrchestratorService,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler as _create_default_crossref_error_handler,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_fallback_service as _create_default_crossref_fallback_service,
)
from bioetl.infrastructure.adapters.crossref._defaults import (
    CROSSREF_DEFAULT_FALLBACK_CONFIG as _CROSSREF_DEFAULT_FALLBACK_CONFIG,
)
from bioetl.infrastructure.adapters.crossref.batch import (
    DoiBatchProcessor,
    SearchPaginator,
)
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_batch_fetcher,
    _create_default_crossref_fetch_flow,
    _create_default_crossref_query_builder,
    _create_default_crossref_response_mapper,
    _create_default_crossref_search_paginator,
    _create_default_crossref_title_fallback_handler,
)
from bioetl.infrastructure.adapters.crossref.fallback import TitleFallbackHandler
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

CROSSREF_API_BASE = "https://api.crossref.org"

CROSSREF_HEALTH_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)


@dataclass
class CrossRefAdapter(BaseHttpAdapter):
    """CrossRef adapter with thin-facade delegation to flow components."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    mailto: str
    batch_size: int = 50
    metrics: MetricsPort | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetrics | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestratorService | None = None
    query_builder: CrossRefQueryBuilder | None = None
    response_mapper: CrossRefResponseMapper | None = None
    batch_fetcher: DoiBatchProcessor | None = None
    search_paginator: SearchPaginator | None = None
    title_fallback_handler: TitleFallbackHandler | None = None
    fetch_flow: CrossRefFetchFlow | None = None

    provider_name: str = field(init=False, default="crossref")
    """Provider identifier (required by DataSourcePort)."""
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)
    _query_builder: CrossRefQueryBuilder = field(init=False, repr=False)
    _response_mapper: CrossRefResponseMapper = field(init=False, repr=False)
    _fetch_flow: CrossRefFetchFlow = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize helper services and decomposed CrossRef flow components."""
        if self.adapter_metrics is not None and self.request_collector is not None:
            self._adapter_metrics = self.adapter_metrics
            self._request_collector = self.request_collector
        else:
            self._init_adapter_metrics()

        self._error_handler = (
            self.error_handler
            if self.error_handler is not None
            else _create_default_crossref_error_handler(
                logger=self.logger,
                metrics=self.metrics,
            )
        )
        self._fallback_fetch_service = (
            self.fallback_fetch_service
            if self.fallback_fetch_service is not None
            else _create_default_crossref_fallback_service(
                adapter_metrics=self._adapter_metrics,
            )
        )

        self._query_builder = (
            self.query_builder
            if self.query_builder is not None
            else _create_default_crossref_query_builder(
                api_base=CROSSREF_API_BASE,
                mailto=self.mailto,
            )
        )
        self._response_mapper = (
            self.response_mapper
            if self.response_mapper is not None
            else _create_default_crossref_response_mapper()
        )

        self._batch_fetcher = (
            self.batch_fetcher
            if self.batch_fetcher is not None
            else _create_default_crossref_batch_fetcher(
                http=self.http_client,
                logger=self.logger,
                metrics=self._adapter_metrics,
                mailto=self.mailto,
                api_base=CROSSREF_API_BASE,
                headers_fn=self._build_headers,
                request_collector=self._request_collector,
            )
        )
        self._search_paginator = (
            self.search_paginator
            if self.search_paginator is not None
            else _create_default_crossref_search_paginator(
                http=self.http_client,
                logger=self.logger,
                metrics=self._adapter_metrics,
                mailto=self.mailto,
                api_base=CROSSREF_API_BASE,
                headers_fn=self._build_headers,
                request_collector=self._request_collector,
            )
        )
        self._fallback_handler = (
            self.title_fallback_handler
            if self.title_fallback_handler is not None
            else _create_default_crossref_title_fallback_handler(
                logger=self.logger,
                search_fn=self._search_paginator.search,
            )
        )
        self.configure_fallback_policy(None)

        self._fetch_flow = (
            self.fetch_flow
            if self.fetch_flow is not None
            else _create_default_crossref_fetch_flow(
                logger=self.logger,
                batch_fetcher=self._batch_fetcher,
                search_paginator=self._search_paginator,
                fallback_decorator=self._fallback_decorator,
                batch_size=self.batch_size,
                response_mapper=self._response_mapper,
            )
        )

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback decorator behavior from provider YAML policy."""
        enabled, config = resolve_fallback_policy(
            policy,
            defaults=_CROSSREF_DEFAULT_FALLBACK_CONFIG,
            default_enabled=True,
        )
        strategy = DefaultFallbackExecutionStrategy(
            normalize_id_hook=normalize_doi,
            extract_record_id_hook=lambda rec: str(rec.get("DOI", "")),
            fallback_handler_hook=self._fallback_handler if enabled else None,
        )
        self._fallback_decorator = ComposableFallbackDecorator(
            service=self._fallback_fetch_service,
            strategy=strategy,
            config=config,
            logger=self.logger,
        )
        if hasattr(self, "_fetch_flow"):
            self._fetch_flow.fallback_decorator = self._fallback_decorator

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with polite pool identification.

        Returns:
            Dictionary of HTTP request headers including the polite pool mailto identifier.
        """
        return self._query_builder.build_headers()

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch CrossRef publications by DOI list (FilterableDataSourcePort)."""
        async for publication in self._fetch_flow.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield publication

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering is not supported by CrossRef API."""
        raise NotImplementedError(
            "CrossRef API does not support multi-field filtering. "
            "Use fetch_filtered() with filter_field='doi' instead."
        )
        yield {}  # pragma: no cover - keeps AsyncIterator contract

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications by DOI with title-search fallback for misses."""
        async for publication in self._fetch_flow.fetch_filtered_with_fallback(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            limit=limit,
        ):
            yield publication

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch CrossRef publications via DOI filters or free-text query."""
        del offset
        async for publication in self._fetch_flow.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            yield publication

    async def _probe_health(self) -> HealthStatus:
        """Probe CrossRef API health with response-status classification.

        Returns:
            HealthStatus reflecting the current CrossRef API availability.
        """
        try:
            url = self._query_builder.build_health_probe_url()
            params = self._query_builder.build_health_probe_params()

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(
                    url,
                    params=params,
                    headers=self._build_headers(),
                )
            elapsed = time.monotonic() - start_time

            probe_mapping = self._response_mapper.map_health_probe(
                status_code=response.status_code,
                elapsed_seconds=elapsed,
            )
            if probe_mapping.event_name == "crossref_health_check_slow":
                self.logger.warning(
                    probe_mapping.event_name,
                    elapsed_seconds=round(elapsed, 2),
                )
            elif probe_mapping.event_name is not None:
                self.logger.warning(
                    probe_mapping.event_name,
                    status_code=response.status_code,
                    classified_status=probe_mapping.status.value,
                )
            return probe_mapping.status

        except CROSSREF_HEALTH_ERRORS as error:
            self.logger.warning(
                "crossref_health_check_failed",
                error=str(error),
            )
            raise

    def _fallback_health_status(self) -> HealthStatus:
        """Return fallback status used when probe execution fails.

        Returns:
            HealthStatus.UNHEALTHY as the safe default when health probe cannot execute.
        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Return endpoint path used for CrossRef health checks.

        Returns:
            Endpoint path string used for health probe requests.
        """
        return "/works"

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Return and clear aggregated API request metadata.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        metadata = self._request_collector.to_source_metadata(
            source_type="api",
            url=CROSSREF_API_BASE,
            api_version=api_version,
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
        """Close adapter resources via underlying HTTP client context manager."""
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)
