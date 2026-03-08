"""Semantic Scholar API adapter facade for publication data extraction."""

from __future__ import annotations

__all__ = ["DEFAULT_FIELDS", "SEMANTICSCHOLAR_HEALTH_ERRORS", "SemanticScholarAdapter"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    DefaultFallbackExecutionStrategy,
    FallbackDecoratorConfig,
    FallbackFetchOrchestratorService,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler as _create_default_semanticscholar_error_handler,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_fallback_service as _create_default_semanticscholar_fallback_service,
)
from bioetl.infrastructure.adapters.semanticscholar.batch_request_mixin import (
    SemanticScholarBatchRequestMixin,
)
from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.semanticscholar.fetch_adapter_mixin import (
    SemanticScholarFetchAdapterMixin,
)
from bioetl.infrastructure.adapters.semanticscholar.health_metadata_mixin import (
    SemanticScholarHealthMetadataMixin,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

DEFAULT_FIELDS = (
    "paperId,externalIds,title,abstract,year,publicationDate,"
    "venue,authors,authors.externalIds,authors.hIndex,authors.authorId,"
    "citationCount,referenceCount,isOpenAccess,"
    "openAccessPdf,tldr,fieldsOfStudy,publicationTypes,journal"
)

SEMANTICSCHOLAR_HEALTH_ERRORS = (
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

_SEMANTICSCHOLAR_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field="doi",
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "SemanticScholar fallback only supports 'doi' filtering, skipping"
    ),
    skip_on_unsupported_filter_field=True,
    primary_lookup_method="doi",
    trim_primary_ids_to_limit=False,
    fallback_operation="fetch_filtered_with_fallback",
)


def _create_default_semanticscholar_title_fallback_handler(
    *,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    metrics: AdapterMetrics,
    api_key: str,
    fields: str,
) -> SemanticScholarTitleFallbackHandler:
    """Create default title fallback handler for non-DI call sites.

    Args:
        http_client: HTTP client for API requests.
        logger: Logger port for structured logging.
        metrics: Adapter metrics for request tracking.
        api_key: Optional Semantic Scholar API key for stable rate limits.
        fields: Comma-separated list of fields to retrieve per paper.

    Returns:
        SemanticScholarTitleFallbackHandler instance configured with HTTP client and API key.
    """
    return SemanticScholarTitleFallbackHandler(
        http_client=http_client,
        logger=logger,
        metrics=metrics,
        api_key=api_key,
        fields=fields,
    )


@dataclass
class SemanticScholarAdapter(
    SemanticScholarHealthMetadataMixin,
    SemanticScholarFetchAdapterMixin,
    SemanticScholarBatchRequestMixin,
    BaseHttpAdapter,
):
    """Semantic Scholar adapter facade with decomposed fetch/health internals."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    api_key: str = ""
    batch_size: int = 100
    fields: str = DEFAULT_FIELDS
    metrics: MetricsPort | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetrics | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestratorService | None = None
    title_fallback_handler: SemanticScholarTitleFallbackHandler | None = None

    provider_name: str = field(init=False, default="semanticscholar")
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize adapter metrics and fallback helper components."""
        if self.adapter_metrics is not None and self.request_collector is not None:
            self._adapter_metrics = self.adapter_metrics
            self._request_collector = self.request_collector
        else:
            self._init_adapter_metrics()
        self._error_handler = (
            self.error_handler
            if self.error_handler is not None
            else _create_default_semanticscholar_error_handler(
                logger=self._logger,
                metrics=self._metrics,
            )
        )
        self._fallback_fetch_service = (
            self.fallback_fetch_service
            if self.fallback_fetch_service is not None
            else _create_default_semanticscholar_fallback_service(
                adapter_metrics=self._adapter_metrics,
            )
        )
        self._fallback_handler = (
            self.title_fallback_handler
            if self.title_fallback_handler is not None
            else _create_default_semanticscholar_title_fallback_handler(
                http_client=self._http_client,
                logger=self._logger,
                metrics=self._adapter_metrics,
                api_key=self.api_key,
                fields=self.fields,
            )
        )
        self.configure_fallback_policy(None)

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback decorator behavior from provider YAML policy.

        Args:
            policy: Provider YAML fallback policy object, or None to use defaults.
        """
        enabled, config = resolve_fallback_policy(
            policy,
            defaults=_SEMANTICSCHOLAR_DEFAULT_FALLBACK_CONFIG,
            default_enabled=True,
        )
        strategy = DefaultFallbackExecutionStrategy(
            normalize_id_hook=self._normalize_doi,
            extract_record_id_hook=lambda rec: str(rec.get("doi", "")),
            fallback_handler_hook=self._fallback_handler if enabled else None,
        )
        self._fallback_decorator = ComposableFallbackDecorator(
            service=self._fallback_fetch_service,
            strategy=strategy,
            config=config,
            logger=self._logger,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with optional API key.

        Returns:
            Dictionary of HTTP headers including optional x-api-key if configured.
        """
        headers = {
            "User-Agent": "BioETL/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key and not self.api_key.startswith("your_"):
            headers["x-api-key"] = self.api_key
        return headers
