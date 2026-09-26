# MRO/override residual on mixin or client hierarchies.
"""OpenAlex data source adapter implementing FilterableDataSourcePort for OpenAlex Works API.

Uses httpx via UnifiedHTTPClient for REST/JSON API access.
Error Handling (RULES.md S3.1): Critical errors (401, 403) fail immediately, recoverable errors handled by retry.
Authentication: OpenAlex API-key access is canonical; optional `mailto` is legacy contact attribution.
"""

from __future__ import annotations

__all__ = [
    "OPENALEX_API_BASE",
    "OPENALEX_RUNTIME_ERRORS",
    "OpenAlexAdapter",
]

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestrator,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR,
)
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)
from bioetl.infrastructure.adapters.openalex.client_runtime_helpers import (
    OpenAlexRuntimeServicesRequest,
    build_openalex_runtime_services,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import (
    OpenAlexCursorFlow,
)
from bioetl.infrastructure.adapters.openalex.fallback import (
    OpenAlexTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
    OpenAlexFallbackOrchestrator,
)
from bioetl.infrastructure.adapters.openalex.filter_fetch_adapter_mixin import (
    OpenAlexAdapterFilterFetchMixin,
)
from bioetl.infrastructure.adapters.openalex.health_adapter_mixin import (
    OpenAlexAdapterHealthMixin,
)
from bioetl.infrastructure.adapters.openalex.query_execution import (
    OpenAlexQueryExecutor,
)
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

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

from bioetl.infrastructure.adapters.openalex._constants import OPENALEX_API_BASE

OPENALEX_RUNTIME_ERRORS = COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR


@dataclass
class OpenAlexAdapter(  # pyright: ignore[reportUnsafeMultipleInheritance]
    OpenAlexAdapterFilterFetchMixin,
    OpenAlexAdapterHealthMixin,
    OpenAlexAdapterHelpersMixin,
    FallbackPolicyMixin,
    BaseHttpAdapter,
):
    """OpenAlex data source adapter.

    Inherits from BaseHttpAdapter for standardized lifecycle management
    and Template Method pattern for health checks.

    Implements DataSourcePort and FilterableDataSourcePort for OpenAlex
    Works API with batch DOI resolution and title fallback support.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        mailto: Optional technical email for legacy request attribution.
        api_key: Optional OpenAlex API key. Required for production-sized use.
            See: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
        batch_size: Number of DOIs per batch request (max 50 recommended).
        metrics: Optional MetricsPort for recording adapter metrics.

    """

    http_client: UnifiedHTTPClient  # pyright: ignore[reportIncompatibleVariableOverride]
    logger: LoggerPort
    mailto: str | None = None
    api_key: str | None = None
    batch_size: int = 50
    metrics: MetricsPort | None = None
    title_search_cache_size: int = 256
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    _: KW_ONLY
    fallback_fetch_service: FallbackFetchOrchestrator
    openalex_query_executor: OpenAlexQueryExecutor | None = None
    openalex_response_mapper: OpenAlexResponseMapper | None = None
    openalex_cursor_flow: OpenAlexCursorFlow | None = None
    title_fallback_handler: OpenAlexTitleFallbackHandler | None = None
    openalex_fallback_orchestrator: OpenAlexFallbackOrchestrator | None = None

    provider_name: str = field(init=False, default="openalex")
    """Provider identifier (required by DataSourcePort)."""
    _fallback_fetch_service: FallbackFetchOrchestrator = field(init=False, repr=False)
    _query_executor: OpenAlexQueryExecutor = field(init=False, repr=False)
    _response_mapper: OpenAlexResponseMapper = field(init=False, repr=False)
    _cursor_flow: OpenAlexCursorFlow = field(init=False, repr=False)
    _fallback_orchestrator: OpenAlexFallbackOrchestrator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize adapter metrics and decomposed OpenAlex components."""
        BaseHttpAdapter.__init__(
            self,
            http_client=self.http_client,
            logger=self.logger,
            metrics=self.metrics,
            dependency_context=self.dependency_context,
            error_handler=self.error_handler,
            adapter_metrics=self.adapter_metrics,
            request_collector=self.request_collector,
        )
        self._fallback_fetch_service = self.fallback_fetch_service
        runtime_request = OpenAlexRuntimeServicesRequest(
            fallback_fetch_service=self._fallback_fetch_service,
            openalex_query_executor=self.openalex_query_executor,
            openalex_response_mapper=self.openalex_response_mapper,
            openalex_cursor_flow=self.openalex_cursor_flow,
            title_fallback_handler=self.title_fallback_handler,
            openalex_fallback_orchestrator=self.openalex_fallback_orchestrator,
            http_client=self.http_client,
            adapter_metrics=self._adapter_metrics,
            request_collector=self._request_collector,
            headers_provider=self._build_headers,
            api_base=OPENALEX_API_BASE,
            mailto=self.mailto,
            api_key=self.api_key,
            batch_size=self.batch_size,
            title_search_cache_size=self.title_search_cache_size,
            normalize_doi=self._normalize_doi,
            escape_title_for_search=self._escape_title_for_search,
            extract_record_id=self._extract_doi_from_record,
            search_by_title=self._search_by_title,
            logger=self._logger,
            runtime_errors=OPENALEX_RUNTIME_ERRORS,
        )
        runtime_services = build_openalex_runtime_services(runtime_request)
        self._query_executor = runtime_services.query_executor
        self._response_mapper = runtime_services.response_mapper
        self._cursor_flow = runtime_services.cursor_flow
        self._fallback_handler = runtime_services.fallback_handler
        self._fallback_orchestrator = runtime_services.fallback_orchestrator
        self.configure_fallback_policy(None)

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback orchestrator behavior from provider YAML policy.

        Args:
            policy: Provider YAML fallback policy object, or None to use defaults.
        """
        self._fallback_orchestrator.configure_policy(policy)
