"""UniProt API adapter facade."""

from __future__ import annotations

__all__ = ["UNIPROT_BATCH_SIZE", "UNIPROT_FETCH_ERRORS", "UniProtAdapter"]

from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError
from typing_extensions import override

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
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

    from bioetl.domain.ports import LoggerPort, MetricsPort
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


class UniProtAdapter(
    UniProtFilteringAdapterMixin,
    UniProtFeatureSequenceAdapterMixin,
    UniProtProteinFetchAdapterMixin,
    UniProtAdapterMetadataMixin,
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
        base_url: str = "https://rest.uniprot.org",
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize UniProt adapter dependencies."""
        super().__init__(http_client, logger, metrics=metrics)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
        self._error_handler = ErrorService(self.logger)
        self._fetch_strategies = {
            "protein": self._fetch_proteins,
            "feature": self._fetch_features,
            "sequence": self._fetch_sequences,
        }
        self._fallback_fetch_service = FallbackFetchOrchestratorService()

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
        """Perform health probe using Ubiquitin P62988 query."""
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
    _settings: Any | None,  # Any: dynamic payload or structural mixin boundary
    **kwargs: Any,  # Any: forwarding arbitrary request kwargs to underlying HTTP client
) -> UniProtAdapter:
    """Factory helper for registry-based adapter construction."""
    if http_client is None:
        raise ValueError("UniProt adapter requires http_client")
    if logger is None:
        raise ValueError("UniProt adapter requires logger")

    return UniProtAdapter(
        http_client=http_client,
        logger=logger,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url", "https://rest.uniprot.org"),
        strict_error_handling=kwargs.get("strict_error_handling", False),
        metrics=kwargs.get("metrics"),
    )
