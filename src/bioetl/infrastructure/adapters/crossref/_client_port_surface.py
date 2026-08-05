# Host attrs/methods provided by concrete CrossRefAdapter composition.
"""Port-facing fetch/health/metadata surface for CrossRefAdapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.crossref._client_ops import (
    crossref_clear_request_collector,
    crossref_fetch,
    crossref_fetch_filtered,
    crossref_fetch_filtered_with_fallback,
    crossref_probe_health,
    crossref_request_count,
    crossref_source_metadata,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryPlanner
    from bioetl.infrastructure.adapters.crossref.response_mapper import (
        CrossRefResponseMapper,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

__all__ = ["_CrossRefPortSurfaceMixin"]


class _CrossRefPortSurfaceMixin:
    """DataSourcePort/Filterable surface methods delegated to flow helpers.

    Host attributes are annotation-only under TYPE_CHECKING so they do not
    become dataclass fields with defaults on CrossRefAdapter.
    """

    CROSSREF_API_BASE: ClassVar[str]
    CROSSREF_HEALTH_ERRORS: ClassVar[tuple[type[Exception], ...]]

    if TYPE_CHECKING:
        http_client: UnifiedHTTPClient
        _logger: LoggerPort
        _adapter_metrics: AdapterMetricsRecorder
        _request_collector: APIRequestCollector | None
        _query_builder: CrossRefQueryPlanner
        _response_mapper: CrossRefResponseMapper
        _fetch_flow: CrossRefFetchFlow | None

    def _require_fetch_flow(self) -> CrossRefFetchFlow:
        """Return fetch flow after ``__post_init__`` wiring (never None in use)."""
        flow = self._fetch_flow
        if flow is None:
            raise RuntimeError("CrossRefAdapter fetch flow is not initialized")
        return flow

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with polite pool identification."""
        return self._query_builder.build_headers()

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch CrossRef publications by DOI list (FilterableDataSourcePort)."""
        async for publication in crossref_fetch_filtered(
            flow=self._require_fetch_flow(),
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield publication

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications by DOI with title-search fallback for misses."""
        async for publication in crossref_fetch_filtered_with_fallback(
            flow=self._require_fetch_flow(),
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
        async for publication in crossref_fetch(
            flow=self._require_fetch_flow(),
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            yield publication

    async def _probe_health(self) -> HealthStatus:
        """Probe CrossRef API health with response-status classification."""
        return await crossref_probe_health(
            http_client=self.http_client,
            query_builder=self._query_builder,
            response_mapper=self._response_mapper,
            adapter_metrics=self._adapter_metrics,
            headers_provider=cast("Callable[[], dict[str, str]]", self._build_headers),
            logger=self._logger,
            health_errors=self.CROSSREF_HEALTH_ERRORS,
        )

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Return and clear aggregated API request metadata."""
        return crossref_source_metadata(
            request_collector=self._request_collector,
            api_base=self.CROSSREF_API_BASE,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        crossref_clear_request_collector(
            request_collector=self._request_collector,
        )

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return crossref_request_count(
            request_collector=self._request_collector,
        )
