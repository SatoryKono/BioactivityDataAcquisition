"""UniProt API adapter facade."""

from __future__ import annotations

__all__ = ["UNIPROT_BATCH_SIZE", "UNIPROT_FETCH_ERRORS", "UniProtAdapter"]

from typing import TYPE_CHECKING, Any, override

from httpx import HTTPStatusError

from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import (
    FallbackDecoratorConfig,
    FallbackFetchOrchestrator,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_TITLE_FALLBACK_ERRORS,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdProtocol,
    NormalizeIdProtocol,
)
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE
from bioetl.infrastructure.adapters.uniprot.feature_sequence_adapter_mixin import (
    UniProtFeatureSequenceAdapterMixin,
)
from bioetl.infrastructure.adapters.uniprot.filtering_adapter_mixin import (
    UniProtFilteringAdapterMixin,
)
from bioetl.infrastructure.adapters.uniprot.health_probe import probe_uniprot_health
from bioetl.infrastructure.adapters.uniprot.metadata_adapter_mixin import (
    UniProtAdapterMetadataMixin,
)
from bioetl.infrastructure.adapters.uniprot.protein_fetch_adapter_mixin import (
    UniProtProteinFetchAdapterMixin,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

UNIPROT_BATCH_SIZE = 100

UNIPROT_FETCH_ERRORS: tuple[type[Exception], ...] = (
    *COMMON_TITLE_FALLBACK_ERRORS,
    HTTPStatusError,
    ConnectionError,
    TimeoutError,
)

_UNIPROT_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field=None,
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "UniProt fallback accepts any filter field with provider-specific hooks"
    ),
    skip_on_unsupported_filter_field=False,
    primary_lookup_method=None,
    trim_primary_ids_to_limit=False,
    fallback_operation="fetch_filtered_with_fallback",
)


class UniProtAdapter(
    UniProtFilteringAdapterMixin,
    UniProtFeatureSequenceAdapterMixin,
    UniProtProteinFetchAdapterMixin,
    UniProtAdapterMetadataMixin,
    FallbackPolicyMixin,
    BaseHttpAdapter,
    PaginatedFetcherMixin,
):
    """UniProt DataSource adapter facade with decomposed internals."""

    provider_name: str = "uniprot"
    http_client: UnifiedHTTPClient

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        *,
        fallback_fetch_service: FallbackFetchOrchestrator,
        api_key: str | None = None,
        base_url: str = UNIPROT_API_BASE,
        strict_error_handling: bool = False,
        dependency_context: HttpAdapterDependencyContext | None = None,
        **legacy_ports: object,
    ) -> None:
        """Initialize UniProt adapter dependencies.

        Optional metrics/error_handler/adapter_metrics/request_collector may be
        passed via ``**legacy_ports`` without growing the S107 parameter budget.
        """
        metrics = legacy_ports.pop("metrics", None)
        error_handler = legacy_ports.pop("error_handler", None)
        adapter_metrics = legacy_ports.pop("adapter_metrics", None)
        request_collector = legacy_ports.pop("request_collector", None)
        if legacy_ports:
            unexpected = ", ".join(sorted(str(k) for k in legacy_ports))
            raise TypeError(
                f"UniProtAdapter() got unexpected keyword argument(s): {unexpected}"
            )
        super().__init__(
            http_client,
            logger,
            metrics=metrics,  # type: ignore[arg-type]
            dependency_context=dependency_context,
            error_handler=error_handler,  # type: ignore[arg-type]
            adapter_metrics=adapter_metrics,  # type: ignore[arg-type]
            request_collector=request_collector,  # type: ignore[arg-type]
        )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
        self._fetch_strategies = {
            "protein": self._fetch_proteins,
            "feature": self._fetch_features,
            "sequence": self._fetch_sequences,
        }
        self._bind_fallback_fetch_service(fallback_fetch_service)
        self.configure_fallback_policy(None)

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return UniProt-specific default fallback config."""
        return _UNIPROT_DEFAULT_FALLBACK_CONFIG

    def _get_normalize_id_hook(self) -> NormalizeIdProtocol:
        """Return accession strip-normalization hook."""
        return lambda value: value.strip()

    def _get_extract_record_id_hook(self) -> ExtractRecordIdProtocol:
        """Return hook extracting accession from a UniProt record."""
        return self._extract_accession_from_record

    @staticmethod
    def _extract_accession_from_record(record: BronzeRecord) -> str | None:
        accession = record.get("accession")
        if not isinstance(accession, str):
            return None
        cleaned = accession.strip()
        return cleaned if cleaned else None

    @override
    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records by query or filter IDs.

        Args:
            entity_type: Entity type to fetch; must be "protein", "feature", or "sequence".
            limit: Optional maximum number of records to yield.
            query: Optional UniProt query string (e.g., "reviewed:true AND organism_id:9606").
            filter_ids: Optional list of accession IDs to filter by.
            filter_field: Optional filter field name; required when filter_ids provided.
            offset: Ignored; internal pagination manages record offset.

        Yields:
            BronzeRecord entries from the UniProt REST API.

        Raises:
            ValueError: If entity_type is not "protein", "feature", or "sequence".
        """
        del offset
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        if filter_ids and filter_field:
            async for record in self.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
            return

        async for record in strategy(query=query, limit=limit):
            yield record

    @override
    async def _probe_health(self) -> HealthStatus:
        """Perform health probe using Ubiquitin P62988 query.

        Returns:
            HealthStatus reflecting the current UniProt API availability.
        """
        try:
            return await probe_uniprot_health(
                base_url=self.base_url,
                provider_name=self.provider_name,
                http_client=self.http_client,
                logger=self._logger,
                adapter_metrics=self._adapter_metrics,
                healthy_status_provider=self._fallback_health_status,
            )
        except UNIPROT_FETCH_ERRORS as error:
            error_type = self._error_handler.get_error_type(error)
            self._logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(error),
            )
            raise


def _create_uniprot_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    _settings: object | None,
    **kwargs: Any,  # Any: forwarding arbitrary kwargs to HTTP client
) -> UniProtAdapter:
    """Factory helper for registry-based adapter construction.

    Args:
        http_client: HTTP client for API requests; raises ValueError if None.
        logger: Logger port for structured logging; raises ValueError if None.
        _settings: Application settings (unused; present for registry signature compatibility).
        **kwargs: Additional keyword arguments forwarded to UniProtAdapter constructor.

    Returns:
        UniProtAdapter instance configured with the given HTTP client and logger.

    Raises:
        ValueError: If http_client or logger is None.
    """
    if http_client is None:
        raise ValueError("UniProt adapter requires http_client")
    if logger is None:
        raise ValueError("UniProt adapter requires logger")
    if "fallback_fetch_service" not in kwargs:
        raise ValueError("UniProt adapter requires fallback_fetch_service")

    return UniProtAdapter(
        http_client=http_client,
        logger=logger,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url", UNIPROT_API_BASE),
        strict_error_handling=kwargs.get("strict_error_handling", False),
        metrics=kwargs.get("metrics"),
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs["fallback_fetch_service"],
    )
