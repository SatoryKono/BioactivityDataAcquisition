"""OpenAlex data source adapter.

Implements FilterableDataSourcePort for OpenAlex Works API.
Rate limits and retry strategy configured via source YAML (``configs/sources/openalex.yaml``).

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

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestratorService,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)
from bioetl.infrastructure.adapters.openalex.client_runtime_helpers import (
    build_openalex_runtime_services,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import (
    OpenAlexCursorFlowService,
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
    from bioetl.infrastructure.config import Settings

from bioetl.infrastructure.adapters.openalex._constants import OPENALEX_API_BASE

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
class OpenAlexAdapter(
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
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    _: KW_ONLY
    fallback_fetch_service: FallbackFetchOrchestratorService
    openalex_query_executor: OpenAlexQueryExecutor | None = None
    openalex_response_mapper: OpenAlexResponseMapper | None = None
    openalex_cursor_flow: OpenAlexCursorFlowService | None = None
    title_fallback_handler: OpenAlexTitleFallbackHandler | None = None
    openalex_fallback_orchestrator: OpenAlexFallbackOrchestrator | None = None

    provider_name: str = field(init=False, default="openalex")
    """Provider identifier (required by DataSourcePort)."""
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _query_executor: OpenAlexQueryExecutor = field(init=False, repr=False)
    _response_mapper: OpenAlexResponseMapper = field(init=False, repr=False)
    _cursor_flow: OpenAlexCursorFlowService = field(init=False, repr=False)
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
        runtime_services = build_openalex_runtime_services(
            fallback_fetch_service=self._fallback_fetch_service,
            openalex_query_executor=self.openalex_query_executor,
            openalex_response_mapper=self.openalex_response_mapper,
            openalex_cursor_flow=self.openalex_cursor_flow,
            title_fallback_handler=self.title_fallback_handler,
            openalex_fallback_orchestrator=self.openalex_fallback_orchestrator,
            http_client=self._http_client,
            adapter_metrics=self._adapter_metrics,
            request_collector=self._request_collector,
            headers_provider=self._build_headers,
            api_base=OPENALEX_API_BASE,
            mailto=self.mailto,
            batch_size=self.batch_size,
            title_search_cache_size=self.title_search_cache_size,
            normalize_doi=self._normalize_doi,
            escape_title_for_search=self._escape_title_for_search,
            extract_record_id=self._extract_doi_from_record,
            search_by_title=self._search_by_title,
            logger=self._logger,
            runtime_errors=OPENALEX_RUNTIME_ERRORS,
        )
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
    if "fallback_fetch_service" not in kwargs:
        raise ValueError("OpenAlex adapter requires fallback_fetch_service")

    return OpenAlexAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs["fallback_fetch_service"],
    )
