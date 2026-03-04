"""Semantic Scholar API adapter facade for publication data extraction."""

from __future__ import annotations

__all__ = ["DEFAULT_FIELDS", "SEMANTICSCHOLAR_HEALTH_ERRORS", "SemanticScholarAdapter"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
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
    from bioetl.domain.ports import LoggerPort, MetricsPort
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

    provider_name: str = field(init=False, default="semanticscholar")
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize adapter metrics and fallback helper components."""
        self._init_adapter_metrics()
        self._fallback_fetch_service = FallbackFetchOrchestratorService()
        self._fallback_handler = SemanticScholarTitleFallbackHandler(
            http_client=self.http_client,
            logger=self.logger,
            metrics=self._adapter_metrics,
            api_key=self.api_key,
            fields=self.fields,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with optional API key."""
        headers = {
            "User-Agent": "BioETL/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key and not self.api_key.startswith("your_"):
            headers["x-api-key"] = self.api_key
        return headers
