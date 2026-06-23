"""Semantic Scholar adapter implementation for publication data extraction.

Canonical provider adapter surface:
    - ``bioetl.infrastructure.adapters.semanticscholar``
    - ``bioetl.infrastructure.adapters.semanticscholar.adapter``
"""

from __future__ import annotations

__all__ = ["DEFAULT_FIELDS", "SEMANTICSCHOLAR_HEALTH_ERRORS", "SemanticScholarAdapter"]

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    FallbackFetchOrchestrator,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.semanticscholar._client_fallback_policy import (
    _SemanticScholarFallbackPolicyMixin,
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
from bioetl.infrastructure.adapters.semanticscholar.request_headers import (
    build_semanticscholar_headers,
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


def _create_default_semanticscholar_title_fallback_handler(
    *,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    metrics: AdapterMetricsRecorder,
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
    _SemanticScholarFallbackPolicyMixin,
    FallbackPolicyMixin,
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
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    _: KW_ONLY
    fallback_fetch_service: FallbackFetchOrchestrator
    title_fallback_handler: SemanticScholarTitleFallbackHandler | None = None

    provider_name: str = field(init=False, default="semanticscholar")
    _fallback_fetch_service: FallbackFetchOrchestrator = field(init=False, repr=False)
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize adapter metrics and fallback helper components."""
        self._bootstrap_dataclass_http_adapter()
        self._bind_fallback_fetch_service(self.fallback_fetch_service)
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

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with optional API key.

        Returns:
            Dictionary of HTTP headers including optional x-api-key if configured.
        """
        return build_semanticscholar_headers(
            self.api_key,
            include_content_type=True,
            skip_placeholder_api_key=True,
        )
