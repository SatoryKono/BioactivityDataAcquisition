# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUnsafeMultipleInheritance=false
# MRO/override residual on mixin or client hierarchies.
"""CrossRef adapter facade for DataSourcePort and FilterableDataSourcePort."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, ClassVar, override

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    FallbackFetchOrchestrator,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_ADAPTER_HEALTH_ERRORS,
)
from bioetl.infrastructure.adapters.crossref._client_fallback_policy import (
    _CrossRefFallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.crossref._client_port_surface import (
    _CrossRefPortSurfaceMixin,
)
from bioetl.infrastructure.adapters.crossref.client_runtime_helpers import (
    build_crossref_fetch_flow,
    build_crossref_runtime_services,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryPlanner
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.types import (
    CrossRefBatchFetcher,
    CrossRefSearchPaginator,
)
from bioetl.infrastructure.adapters.filterable_mixin import NotSupportedMultiFilterMixin

__all__ = [
    "CROSSREF_API_BASE",
    "CROSSREF_HEALTH_ERRORS",
    "CrossRefAdapter",
    "CrossRefFetchFlow",
    "CrossRefQueryPlanner",
    "CrossRefResponseMapper",
]
if TYPE_CHECKING:
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

CROSSREF_HEALTH_ERRORS = COMMON_ADAPTER_HEALTH_ERRORS


@dataclass
class CrossRefAdapter(
    _CrossRefPortSurfaceMixin,
    _CrossRefFallbackPolicyMixin,
    FallbackPolicyMixin,
    NotSupportedMultiFilterMixin,
    BaseHttpAdapter,
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
    fallback_fetch_service: FallbackFetchOrchestrator
    query_builder: CrossRefQueryPlanner | None = None
    response_mapper: CrossRefResponseMapper | None = None
    batch_fetcher: CrossRefBatchFetcher | None = None
    search_paginator: CrossRefSearchPaginator | None = None
    title_fallback_handler: CrossRefTitleFallbackHandler | None = None
    fetch_flow: CrossRefFetchFlow | None = None

    provider_name: str = field(init=False, default="crossref")  # DataSourcePort ID
    unsupported_multi_filter_message: ClassVar[str] = (
        "CrossRef API does not support multi-field filtering. "
        "Use fetch_filtered() with a single filter_field instead."
    )
    CROSSREF_API_BASE: ClassVar[str] = CROSSREF_API_BASE
    CROSSREF_HEALTH_ERRORS: ClassVar[tuple[type[Exception], ...]] = (
        CROSSREF_HEALTH_ERRORS
    )
    _fallback_fetch_service: FallbackFetchOrchestrator = field(init=False, repr=False)
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)
    _query_builder: CrossRefQueryPlanner = field(init=False, repr=False)
    _response_mapper: CrossRefResponseMapper = field(init=False, repr=False)
    _fetch_flow: CrossRefFetchFlow | None = field(init=False, default=None, repr=False)

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
        # Build decorator before fetch flow; hook no-ops while _fetch_flow is None.
        self.configure_fallback_policy(None)
        if self._fallback_decorator is None:
            raise RuntimeError("CrossRef fallback decorator was not configured")

        self._fetch_flow = build_crossref_fetch_flow(
            fetch_flow=self.fetch_flow,
            logger=self._logger,
            batch_fetcher=self._batch_fetcher,
            search_paginator=self._search_paginator,
            fallback_decorator=self._fallback_decorator,
            batch_size=self.batch_size,
            response_mapper=self._response_mapper,
        )

    @override
    def _fallback_health_status(self) -> HealthStatus:
        """Return the safe default status when health probing fails."""
        return HealthStatus.UNHEALTHY

    @override
    def _get_health_endpoint(self) -> str:
        """Return the endpoint path used for CrossRef health checks."""
        return "/works"

    async def aclose(self) -> None:
        """Close HTTP client only when this adapter holds an entered context.

        Injected clients that were never entered (depth 0) are left to their
        outer owner. When the client exposes enter-depth tracking and depth
        is zero, skip close. Clients without depth metadata (or depth >= 1)
        still close via ``__aexit__`` so sole ownership and legacy mocks work.
        """
        if not self.http_client:
            return
        depth: int | None = None
        enter_depth_fn = getattr(type(self.http_client), "_enter_depth", None)
        if callable(enter_depth_fn):
            try:
                raw = enter_depth_fn(self.http_client)
            except TypeError:
                raw = None
            if isinstance(raw, int | float):
                depth = int(raw)
        if depth is None:
            raw_attr = getattr(self.http_client, "_client_enter_depth", None)
            if isinstance(raw_attr, int | float):
                depth = int(raw_attr)
        if depth == 0:
            return
        await self.http_client.__aexit__(None, None, None)
