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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)
from bioetl.infrastructure.adapters.openalex.cursor_flow import (
    OpenAlexCursorFlowService,
)
from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler
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
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
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


def _create_default_openalex_error_handler(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> ErrorHandlerPort:
    """Create default adapter error handler for non-DI call sites."""
    from bioetl.infrastructure.adapters.error_handling import ErrorService

    return ErrorService(logger, metrics=metrics)


def _create_default_openalex_fallback_service(
    *,
    adapter_metrics: AdapterMetrics,
) -> FallbackFetchOrchestratorService:
    """Create fallback orchestrator service for non-DI call sites."""
    return FallbackFetchOrchestratorService(adapter_metrics)


def _create_default_openalex_query_executor(
    *,
    http_client: UnifiedHTTPClient,
    adapter_metrics: AdapterMetrics,
    request_collector: APIRequestCollector,
    headers_provider: Any,  # Any: callable returning dict[str, str]
    api_base: str,
) -> OpenAlexQueryExecutor:
    """Create default query executor for non-DI call sites."""
    return OpenAlexQueryExecutor(
        http_client=http_client,
        adapter_metrics=adapter_metrics,
        request_collector=request_collector,
        headers_provider=headers_provider,
        api_base=api_base,
    )


def _create_default_openalex_response_mapper() -> OpenAlexResponseMapper:
    """Create default response mapper for non-DI call sites."""
    return OpenAlexResponseMapper()


def _create_default_openalex_cursor_flow(
    *,
    mailto: str,
    batch_size: int,
    title_search_cache_size: int,
    normalize_doi: Any,  # Any: callable (str) -> str for DOI normalization
    escape_title_for_search: Any,  # Any: callable (str) -> str for title escaping
    query_executor: OpenAlexQueryExecutor,
    response_mapper: OpenAlexResponseMapper,
    logger: LoggerPort,
    runtime_errors: tuple[type[Exception], ...],
) -> OpenAlexCursorFlowService:
    """Create default cursor flow service for non-DI call sites."""
    return OpenAlexCursorFlowService(
        mailto=mailto,
        batch_size=batch_size,
        title_search_cache_size=title_search_cache_size,
        normalize_doi=normalize_doi,
        escape_title_for_search=escape_title_for_search,
        query_executor=query_executor,
        response_mapper=response_mapper,
        logger=logger,
        runtime_errors=runtime_errors,
    )


def _create_default_openalex_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: Any,  # Any: async callable for title search
) -> TitleFallbackHandler:
    """Create default title fallback handler for non-DI call sites."""
    return TitleFallbackHandler(logger=logger, search_fn=search_fn)


def _create_default_openalex_fallback_orchestrator(
    *,
    fallback_fetch_service: FallbackFetchOrchestratorService,
    fallback_handler: TitleFallbackHandler,
    normalize_id: Any,  # Any: callable (str) -> str for ID normalization
    extract_record_id: Any,  # Any: callable (dict) -> str for record ID extraction
    logger: LoggerPort,
) -> OpenAlexFallbackOrchestrator:
    """Create default fallback orchestrator for non-DI call sites."""
    return OpenAlexFallbackOrchestrator(
        fallback_fetch_service=fallback_fetch_service,
        fallback_handler=fallback_handler,
        normalize_id=normalize_id,
        extract_record_id=extract_record_id,
        logger=logger,
    )


@dataclass
class OpenAlexAdapter(
    OpenAlexAdapterFilterFetchMixin,
    OpenAlexAdapterHealthMixin,
    OpenAlexAdapterHelpersMixin,
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
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetrics | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestratorService | None = None
    openalex_query_executor: OpenAlexQueryExecutor | None = None
    openalex_response_mapper: OpenAlexResponseMapper | None = None
    openalex_cursor_flow: OpenAlexCursorFlowService | None = None
    title_fallback_handler: TitleFallbackHandler | None = None
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
        if self.adapter_metrics is not None and self.request_collector is not None:
            self._adapter_metrics = self.adapter_metrics
            self._request_collector = self.request_collector
        else:
            self._init_adapter_metrics()
        self._error_handler = (
            self.error_handler
            if self.error_handler is not None
            else _create_default_openalex_error_handler(
                logger=self.logger,
                metrics=self.metrics,
            )
        )
        self._fallback_fetch_service = (
            self.fallback_fetch_service
            if self.fallback_fetch_service is not None
            else _create_default_openalex_fallback_service(
                adapter_metrics=self._adapter_metrics,
            )
        )
        self._query_executor = (
            self.openalex_query_executor
            if self.openalex_query_executor is not None
            else _create_default_openalex_query_executor(
                http_client=self.http_client,
                adapter_metrics=self._adapter_metrics,
                request_collector=self._request_collector,
                headers_provider=self._build_headers,
                api_base=OPENALEX_API_BASE,
            )
        )
        self._response_mapper = (
            self.openalex_response_mapper
            if self.openalex_response_mapper is not None
            else _create_default_openalex_response_mapper()
        )
        self._cursor_flow = (
            self.openalex_cursor_flow
            if self.openalex_cursor_flow is not None
            else _create_default_openalex_cursor_flow(
                mailto=self.mailto,
                batch_size=self.batch_size,
                title_search_cache_size=self.title_search_cache_size,
                normalize_doi=self._normalize_doi,
                escape_title_for_search=self._escape_title_for_search,
                query_executor=self._query_executor,
                response_mapper=self._response_mapper,
                logger=self.logger,
                runtime_errors=OPENALEX_RUNTIME_ERRORS,
            )
        )

        self._fallback_handler = (
            self.title_fallback_handler
            if self.title_fallback_handler is not None
            else _create_default_openalex_title_fallback_handler(
                logger=self.logger,
                search_fn=self._search_by_title,
            )
        )
        self._fallback_orchestrator = (
            self.openalex_fallback_orchestrator
            if self.openalex_fallback_orchestrator is not None
            else _create_default_openalex_fallback_orchestrator(
                fallback_fetch_service=self._fallback_fetch_service,
                fallback_handler=self._fallback_handler,
                normalize_id=self._normalize_doi,
                extract_record_id=self._extract_doi_from_record,
                logger=self.logger,
            )
        )
        self.configure_fallback_policy(None)

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback orchestrator behavior from provider YAML policy."""
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

    return OpenAlexAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs.get("fallback_fetch_service"),
    )
