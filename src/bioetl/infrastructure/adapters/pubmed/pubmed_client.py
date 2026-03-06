# src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py
"""PubMed adapter for Entrez E-utilities API.

Implements DataSourcePort for PubMed article metadata extraction.
Split into mixins to comply with LOC limits.
"""

from __future__ import annotations

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    ComposableFallbackDecorator,
    DefaultFallbackExecutionStrategy,
    FallbackDecoratorConfig,
    FallbackFetchOrchestratorService,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.filterable_mixin import NotSupportedMultiFilterMixin
from bioetl.infrastructure.adapters.pubmed._fetch import PubMedFetchMixin
from bioetl.infrastructure.adapters.pubmed._health import PubMedHealthMixin
from bioetl.infrastructure.adapters.pubmed._search import PubMedSearchMixin
from bioetl.infrastructure.adapters.pubmed.adapter_filter_fetch_mixin import (
    PubMedAdapterFilterFetchMixin,
)
from bioetl.infrastructure.adapters.pubmed.constants import (
    ENTREZ_API_BASE as PUBMED_ENTREZ_API_BASE,
)
from bioetl.infrastructure.adapters.pubmed.fallback import TitleFallbackHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

# Mapping from entity_type to DTO model class
PUBMED_DTO_MODELS: dict[str, type[BaseModel]] = {
    "publication": ArticleRecord,
}

# Re-export for tests/importers expecting this symbol on the client module.
ENTREZ_API_BASE = PUBMED_ENTREZ_API_BASE


def _create_default_pubmed_error_handler(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> ErrorHandlerPort:
    """Create default adapter error handler for non-DI call sites."""
    from bioetl.infrastructure.adapters.error_handling import ErrorService

    return ErrorService(logger, metrics=metrics)


def _create_default_pubmed_fallback_service(
    *,
    adapter_metrics: AdapterMetrics,
) -> FallbackFetchOrchestratorService:
    """Create fallback orchestrator service for non-DI call sites."""
    return FallbackFetchOrchestratorService(adapter_metrics)


def _create_default_pubmed_title_fallback_handler(
    *,
    logger: LoggerPort,
    search_fn: Any,
) -> TitleFallbackHandler:
    """Create default title fallback handler for non-DI call sites."""
    return TitleFallbackHandler(logger=logger, search_fn=search_fn)


_PUBMED_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field=None,
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message="PubMed fallback accepts any field and resolves via PMID/title phases",
    skip_on_unsupported_filter_field=False,
    primary_lookup_method="pmid",
    trim_primary_ids_to_limit=False,
    fallback_operation="fetch_filtered_with_fallback",
)


@dataclass
class PubMedAdapter(
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

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None = None
    batch_size: int = 200
    metrics: MetricsPort | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetrics | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestratorService | None = None
    title_fallback_handler: TitleFallbackHandler | None = None

    provider_name: str = field(init=False, default="pubmed")
    _fallback_fetch_service: FallbackFetchOrchestratorService = field(
        init=False, repr=False
    )
    _fallback_decorator: ComposableFallbackDecorator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize metrics, error handler and fallback handler."""
        if self.adapter_metrics is not None and self.request_collector is not None:
            self._adapter_metrics = self.adapter_metrics
            self._request_collector = self.request_collector
        else:
            self._init_adapter_metrics()
        self._error_handler = (
            self.error_handler
            if self.error_handler is not None
            else _create_default_pubmed_error_handler(
                logger=self.logger,
                metrics=self.metrics,
            )
        )
        self._fallback_fetch_service = (
            self.fallback_fetch_service
            if self.fallback_fetch_service is not None
            else _create_default_pubmed_fallback_service(
                adapter_metrics=self._adapter_metrics,
            )
        )

        self._fallback_handler = (
            self.title_fallback_handler
            if self.title_fallback_handler is not None
            else _create_default_pubmed_title_fallback_handler(
                logger=self.logger,
                search_fn=self._search_by_title,
            )
        )
        self.configure_fallback_policy(None)

    def configure_fallback_policy(self, policy: object | None) -> None:
        """Configure fallback decorator behavior from provider YAML policy."""
        enabled, config = resolve_fallback_policy(
            policy,
            defaults=_PUBMED_DEFAULT_FALLBACK_CONFIG,
            default_enabled=True,
        )
        strategy = DefaultFallbackExecutionStrategy(
            normalize_id_hook=lambda value: value.lower().strip(),
            extract_record_id_hook=lambda rec: str(rec.get("pmid", "")),
            fallback_handler_hook=self._fallback_handler if enabled else None,
        )
        self._fallback_decorator = ComposableFallbackDecorator(
            service=self._fallback_fetch_service,
            strategy=strategy,
            config=config,
            logger=self.logger,
        )

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
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


def _create_pubmed_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adap...
) -> PubMedAdapter:
    email = kwargs.get("email")
    if not email and settings:
        email = getattr(settings, "default_email", None)
    if not email:
        raise ValueError("PubMed adapter requires email")

    api_key = kwargs.get("api_key")
    if not api_key and settings and hasattr(settings, "pubmed_api_key"):
        pubmed_key = settings.pubmed_api_key
        if pubmed_key:
            api_key = pubmed_key.get_secret_value()

    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")

    return PubMedAdapter(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=kwargs.get("metrics"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs.get("fallback_fetch_service"),
    )
