# MRO/override residual on mixin or client hierarchies.
"""PubMed adapter implementation for Entrez E-utilities API.

Canonical provider adapter surface:
    - ``bioetl.infrastructure.adapters.pubmed``
    - ``bioetl.infrastructure.adapters.pubmed.adapter``
"""

from __future__ import annotations

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter", "create_pubmed_adapter"]

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    FallbackFetchOrchestrator,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.filterable_mixin import NotSupportedMultiFilterMixin
from bioetl.infrastructure.adapters.pubmed._client_fallback_policy import (
    _PubMedFallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.pubmed._fetch import PubMedFetchMixin
from bioetl.infrastructure.adapters.pubmed._health import PubMedHealthMixin
from bioetl.infrastructure.adapters.pubmed._search import PubMedSearchMixin
from bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin import (
    PubMedAdapterFilterFetchMixin,
)
from bioetl.infrastructure.adapters.pubmed.constants import (
    ENTREZ_API_BASE as PUBMED_ENTREZ_API_BASE,
)
from bioetl.infrastructure.adapters.pubmed.fallback import PubMedTitleFallbackHandler

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

# Mapping from entity_type to DTO model class
PUBMED_DTO_MODELS: dict[str, type[BaseModel]] = {
    "publication": ArticleRecord,
}

# Re-export for tests/importers expecting this symbol on the client module.
ENTREZ_API_BASE = PUBMED_ENTREZ_API_BASE


def _create_default_pubmed_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: Any,  # Any: async callable for title search
) -> PubMedTitleFallbackHandler:
    """Create default title fallback handler for non-DI call sites.

    Returns:
        PubMedTitleFallbackHandler instance configured with the given logger and search function.
    """
    return PubMedTitleFallbackHandler(logger=logger, search_fn=search_fn)


@dataclass
class PubMedAdapter(  # pyright: ignore[reportUnsafeMultipleInheritance]
    _PubMedFallbackPolicyMixin,
    FallbackPolicyMixin,
    NotSupportedMultiFilterMixin,
    PubMedAdapterFilterFetchMixin,
    PubMedFetchMixin,
    PubMedSearchMixin,
    PubMedHealthMixin,
    BaseHttpAdapter,
):
    """PubMed adapter using UnifiedHTTPClient.

    Implements DataSourcePort and FilterableDataSourcePort.
    Functionality split across mixins:
    - PubMedSearchMixin: esearch and title search
    - PubMedFetchMixin: efetch and record yielding
    - PubMedHealthMixin: health probes and metadata
    """

    http_client: UnifiedHTTPClient  # pyright: ignore[reportIncompatibleVariableOverride]
    logger: LoggerPort
    # Technical NCBI contact email for API identification; record-level hashing
    # and anonymization apply to extracted payload fields, not this credential.
    email: str
    api_key: str | None = None
    batch_size: int = 200
    metrics: MetricsPort | None = None
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    _: KW_ONLY
    fallback_fetch_service: FallbackFetchOrchestrator
    title_fallback_handler: PubMedTitleFallbackHandler | None = None

    provider_name: str = field(init=False, default="pubmed")
    _fallback_fetch_service: FallbackFetchOrchestrator = field(init=False, repr=False)
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize metrics, error handler and fallback handler."""
        self._bootstrap_dataclass_http_adapter()
        self._bind_fallback_fetch_service(self.fallback_fetch_service)

        self._fallback_handler = (
            self.title_fallback_handler
            if self.title_fallback_handler is not None
            else _create_default_pubmed_title_fallback_handler(
                logger=self._logger,
                search_fn=self._search_by_title,
            )
        )
        self.configure_fallback_policy(None)

    async def fetch_as_models(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        *,
        validate: bool = True,
    ) -> AsyncIterator[BaseModel]:
        """Fetch PubMed records as typed DTO models.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            validate: Whether to validate.

        Returns:
            Async iterator yielding fetched records.
        """
        model_class = PUBMED_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(f"No DTO model for entity_type '{entity_type}'")

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            dto_data = {
                "pmid": record.get("pmid"),
                "title": record.get("article_title"),
                "raw_xml": record.get("_raw_xml"),
            }
            if validate:
                yield model_class.model_validate(dto_data)
            else:
                yield model_class.model_construct(**dto_data)

    async def aclose(self) -> None:
        """Close adapter resources."""
        await self._close_http_client_context()


from bioetl.infrastructure.adapters.pubmed._adapter_support import (  # noqa: E402
    _create_pubmed_adapter,
)

create_pubmed_adapter = _create_pubmed_adapter
