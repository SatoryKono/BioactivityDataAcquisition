"""UniProt API adapter facade."""

from __future__ import annotations

__all__ = ["UNIPROT_BATCH_SIZE", "UNIPROT_FETCH_ERRORS", "UniProtAdapter"]

from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError
from typing_extensions import override

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.common import (
    FallbackDecoratorConfig,
    FallbackFetchOrchestratorService,
    FallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_fallback_service as _create_default_uniprot_fallback_service,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    ExtractRecordIdHook,
    NormalizeIdHook,
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
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

UNIPROT_BATCH_SIZE = 100

UNIPROT_FETCH_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    ConnectionError,
    TimeoutError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
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

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        api_key: str | None = None,
        base_url: str = UNIPROT_API_BASE,
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
        error_handler: ErrorHandlerPort | None = None,
        adapter_metrics: AdapterMetrics | None = None,
        request_collector: APIRequestCollector | None = None,
        fallback_fetch_service: FallbackFetchOrchestratorService | None = None,
    ) -> None:
        """Initialize UniProt adapter dependencies."""
        super().__init__(
            http_client,
            logger,
            metrics=metrics,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
        )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
        self._fetch_strategies = {
            "protein": self._fetch_proteins,
            "feature": self._fetch_features,
            "sequence": self._fetch_sequences,
        }
        self._fallback_fetch_service = (
            fallback_fetch_service
            if fallback_fetch_service is not None
            else _create_default_uniprot_fallback_service(
                adapter_metrics=self._adapter_metrics,
            )
        )
        self.configure_fallback_policy(None)

    def _get_default_fallback_config(self) -> FallbackDecoratorConfig:
        """Return UniProt-specific default fallback config."""
        return _UNIPROT_DEFAULT_FALLBACK_CONFIG

    def _get_normalize_id_hook(self) -> NormalizeIdHook:
        """Return accession strip-normalization hook."""
        return lambda value: value.strip()

    def _get_extract_record_id_hook(self) -> ExtractRecordIdHook:
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
        """Fetch records by query or filter IDs."""
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
                logger=self.logger,
                adapter_metrics=self._adapter_metrics,
                healthy_status_provider=self._fallback_health_status,
            )
        except UNIPROT_FETCH_ERRORS as error:
            error_type = self._error_handler.get_error_type(error)
            self.logger.warning(
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

    Returns:
        UniProtAdapter instance configured with the given HTTP client and logger.
    """
    if http_client is None:
        raise ValueError("UniProt adapter requires http_client")
    if logger is None:
        raise ValueError("UniProt adapter requires logger")

    return UniProtAdapter(
        http_client=http_client,
        logger=logger,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url", UNIPROT_API_BASE),
        strict_error_handling=kwargs.get("strict_error_handling", False),
        metrics=kwargs.get("metrics"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs.get("fallback_fetch_service"),
    )
