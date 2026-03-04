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
from bioetl.domain.types import BronzeRecord, HealthStatus, JsonDict
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
from bioetl.infrastructure.adapters.openalex.health_probe import probe_openalex_health
from bioetl.infrastructure.adapters.openalex.query_execution import (
    OpenAlexQueryExecutor,
)
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
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
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _query_executor: OpenAlexQueryExecutor = field(init=False, repr=False)
    _response_mapper: OpenAlexResponseMapper = field(init=False, repr=False)
    _cursor_flow: OpenAlexCursorFlowService = field(init=False, repr=False)
    _fallback_orchestrator: OpenAlexFallbackOrchestrator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize adapter metrics and decomposed OpenAlex components."""
        self._init_adapter_metrics()
        self._fallback_fetch_service = FallbackFetchOrchestratorService(
            self._adapter_metrics
        )
        self._query_executor = OpenAlexQueryExecutor(
            http_client=self.http_client,
            adapter_metrics=self._adapter_metrics,
            request_collector=self._request_collector,
            headers_provider=self._build_headers,
            api_base=OPENALEX_API_BASE,
        )
        self._response_mapper = OpenAlexResponseMapper()
        self._cursor_flow = OpenAlexCursorFlowService(
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

        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_by_title,
        )
        self._fallback_orchestrator = OpenAlexFallbackOrchestrator(
            fallback_fetch_service=self._fallback_fetch_service,
            fallback_handler=self._fallback_handler,
            normalize_id=self._normalize_doi,
            extract_record_id=self._extract_doi_from_record,
            logger=self.logger,
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
    ) -> JsonDict:  # Any: untyped OpenAlex API payload
        """Backward-compatible wrapper around query-execution component."""
        return await self._query_executor.request_works_payload(params)

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
        """Fetch OpenAlex works by DOI list via cursor-flow component."""
        async for work in self._cursor_flow.iter_filtered_by_doi(filter_ids, limit):
            yield work

    async def _fetch_filtered_by_title(
        self,
        titles: list[str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch works by title via cursor-flow component."""
        async for work in self._cursor_flow.iter_filtered_by_title(titles, limit):
            yield work

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
        start_count: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 DOI lookup via cursor-flow component."""
        async for work in self._cursor_flow.iter_doi_batches_for_fallback(
            primary_ids=valid_dois,
            limit=limit,
            start_count=start_count,
        ):
            yield work

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

        def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            return self._batch_doi_lookup(primary_ids, request_limit)

        async for work in self._fallback_orchestrator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
        ):
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
        """Fetch works with cursor pagination via cursor-flow component."""
        async for work in self._cursor_flow.iter_query_results(
            query=query, limit=limit
        ):
            yield work

    async def _fetch_by_dois(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Fetch works by DOI via cursor-flow component."""
        async for work in self._cursor_flow.iter_by_dois(dois):
            yield work

    async def _search_by_title(self, title: str, limit: int = 3) -> list[BronzeRecord]:
        """Search works by title via cursor-flow component."""
        return await self._cursor_flow.search_by_title(title, limit)

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
