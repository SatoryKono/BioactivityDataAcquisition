"""CrossRef adapter facade for DataSourcePort and FilterableDataSourcePort."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    FallbackFetchOrchestratorService,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.filterable_mixin import raising_async_iterator
from bioetl.infrastructure.adapters.crossref._client_fallback_policy import (
    _CrossRefFallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.crossref.client_fetch_helpers import (
    aclose_crossref_http_client,
    fetch_crossref_publications,
    fetch_crossref_publications_filtered,
    fetch_crossref_publications_with_fallback,
    raise_crossref_multifilter_not_supported,
)
from bioetl.infrastructure.adapters.crossref.client_observability_helpers import (
    build_crossref_source_metadata,
    clear_crossref_request_collector,
    get_crossref_request_count,
    probe_crossref_health,
)
from bioetl.infrastructure.adapters.crossref.client_runtime_helpers import (
    build_crossref_fetch_flow,
    build_crossref_runtime_services,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.types import (
    CrossRefBatchFetcher,
    CrossRefSearchPaginator,
)

__all__ = [
    "CROSSREF_API_BASE",
    "CROSSREF_HEALTH_ERRORS",
    "CrossRefAdapter",
    "CrossRefFetchFlow",
    "CrossRefQueryBuilder",
    "CrossRefResponseMapper",
]
if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
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
class CrossRefAdapter(
    _CrossRefFallbackPolicyMixin, FallbackPolicyMixin, BaseHttpAdapter
):
    """CrossRef adapter with thin-facade delegation to flow components."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    mailto: str
    batch_size: int = 50
    metrics: MetricsPort | None = None
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    _: KW_ONLY
    fallback_fetch_service: FallbackFetchOrchestratorService
    query_builder: CrossRefQueryBuilder | None = None
    response_mapper: CrossRefResponseMapper | None = None
    batch_fetcher: CrossRefBatchFetcher | None = None
    search_paginator: CrossRefSearchPaginator | None = None
    title_fallback_handler: CrossRefTitleFallbackHandler | None = None
    fetch_flow: CrossRefFetchFlow | None = None

    provider_name: str = field(init=False, default="crossref")  # DataSourcePort ID
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)
    _query_builder: CrossRefQueryBuilder = field(init=False, repr=False)
    _response_mapper: CrossRefResponseMapper = field(init=False, repr=False)
    _fetch_flow: CrossRefFetchFlow = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize helper services and decomposed CrossRef flow components."""
        self._bootstrap_dataclass_http_adapter()
        self._bind_fallback_fetch_service(self.fallback_fetch_service)

        runtime_services = build_crossref_runtime_services(
            query_builder=self.query_builder,
            response_mapper=self.response_mapper,
            batch_fetcher=self.batch_fetcher,
            search_paginator=self.search_paginator,
            title_fallback_handler=self.title_fallback_handler,
        )
        self._query_builder = runtime_services.query_builder
        self._response_mapper = runtime_services.response_mapper
        self._batch_fetcher = runtime_services.batch_fetcher
        self._search_paginator = runtime_services.search_paginator
        self._fallback_handler = runtime_services.fallback_handler
        self.configure_fallback_policy(None)

        self._fetch_flow = build_crossref_fetch_flow(
            fetch_flow=self.fetch_flow,
            logger=self._logger,
            batch_fetcher=self._batch_fetcher,
            search_paginator=self._search_paginator,
            fallback_decorator=self._fallback_decorator,
            batch_size=self.batch_size,
            response_mapper=self._response_mapper,
        )

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
        async for publication in fetch_crossref_publications_filtered(
            fetch_flow=self._fetch_flow,
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield publication

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Multi-field filtering is not supported by CrossRef API."""
        del entity_type, filters, limit
        return raising_async_iterator(
            NotImplementedError(
                "CrossRef API does not support multi-field filtering. "
                "Use fetch_filtered() with a single filter_field instead."
            )
        )

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications by DOI with title-search fallback for misses."""
        async for publication in fetch_crossref_publications_with_fallback(
            fetch_flow=self._fetch_flow,
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
        async for publication in fetch_crossref_publications(
            fetch_flow=self._fetch_flow,
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
        return await probe_crossref_health(
            http_client=self._http_client,
            query_builder=self._query_builder,
            response_mapper=self._response_mapper,
            adapter_metrics=self._adapter_metrics,
            headers_provider=self._build_headers,
            logger=self._logger,
            health_errors=CROSSREF_HEALTH_ERRORS,
        )

    def _fallback_health_status(self) -> HealthStatus:
        """Return the safe default status when health probing fails."""
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Return the endpoint path used for CrossRef health checks."""
        return "/works"

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Return and clear aggregated API request metadata.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        return build_crossref_source_metadata(
            request_collector=self._request_collector,
            api_base=CROSSREF_API_BASE,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        clear_crossref_request_collector(
            request_collector=self._request_collector,
        )

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return get_crossref_request_count(
            request_collector=self._request_collector,
        )

    async def aclose(self) -> None:
        """Close adapter resources via underlying HTTP client context manager."""
        await aclose_crossref_http_client(http_client=self._http_client)
