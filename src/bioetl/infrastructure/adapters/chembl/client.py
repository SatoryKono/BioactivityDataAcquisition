# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUnsafeMultipleInheritance=false
# MRO/override residual on mixin or client hierarchies.
"""ChEMBL data source adapter implementing DataSourcePort.

Health-aware fetching: HEALTHY=full batch, DEGRADED=batch/2, UNHEALTHY=fail fast.
"""

from __future__ import annotations

__all__ = ["ChemblAdapter"]

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.chembl._client_request_helpers import (
    batch_ids,
    build_filter_in_params,
    build_filter_params,
    build_request_params,
    check_duplicate_composite,
    check_duplicate_record,
    compute_record_composite_key,
    get_api_dedup_fields,
    get_api_pk_field,
    iter_chembl_as_models,
    normalize_filter_field,
    process_chembl_response,
    projected_url_length,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import (
    ChemblEntityMapper,
)
from bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin import (
    ChemblFetchAdapterMixin,
)
from bioetl.infrastructure.adapters.chembl.health import ChemblHealthMixin
from bioetl.infrastructure.adapters.chembl.metadata import ChemblMetadataMixin

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
    )
    from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
        FallbackFetchOrchestrator,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass
class ChemblAdapter(
    ChemblFetchAdapterMixin, ChemblHealthMixin, ChemblMetadataMixin, BaseHttpAdapter
):
    """ChEMBL REST adapter with pagination, filtering, and resilience helpers."""

    # Explicit ``field()`` declarations prevent dataclasses from treating
    # same-named class attributes on mixins as inherited defaults.
    http_client: UnifiedHTTPClient = field()
    logger: LoggerPort = field()
    adapter_config: AdapterConfig | None = None
    thread_pool: ThreadPoolExecutor | None = None
    metrics: MetricsPort | None = None
    extraction_params: ExtractionParams | None = None
    dependency_context: HttpAdapterDependencyContext | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetricsRecorder | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestrator | None = None

    provider_name: str = field(init=False, default="chembl")

    _page_size: int = field(init=False, default=1000)
    _filter_batch_size: int = field(init=False, default=20)
    _mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)
    _extraction_params: ExtractionParams = field(
        init=False, default_factory=ExtractionParams.empty
    )

    def __post_init__(self) -> None:
        """Initialize adapter with config values and metrics."""
        self._bootstrap_dataclass_http_adapter()
        config = (
            self.adapter_config if self.adapter_config is not None else AdapterConfig()
        )
        self.adapter_config = config
        self._adapter_config = config
        self._page_size = config.page_size
        self._filter_batch_size = config.batch_size
        self._extraction_params = self.extraction_params or ExtractionParams.empty()
        if not self._extraction_params.is_empty:
            self._logger.info(
                "chembl_extraction_params_configured",
                provider="chembl",
                param_count=len(self._extraction_params.params),
                query_string=self._extraction_params.to_query_string(),
            )

    @property
    def effective_batch_size(self) -> int:
        """Get configured page size for API requests."""
        return self._page_size

    def _build_params(self, offset: int, entity_type: str | None = None) -> JsonDict:
        """Build API request parameters with health-aware batch size."""
        return build_request_params(
            offset=offset,
            entity_type=entity_type,
            page_size=self._get_effective_batch_size(),
            extraction_params=self._extraction_params,
        )

    def _process_response(
        self, response: Response, entity_type: str
    ) -> tuple[list[BronzeRecord], bool]:
        """Process API response and return records with pagination flag."""
        return process_chembl_response(
            response=response, entity_type=entity_type, mapper=self._mapper
        )

    def _batch_ids(self, ids: list[str], batch_size: int) -> Iterator[list[str]]:
        """Split IDs into batches for API requests."""
        return batch_ids(ids, batch_size)

    def _build_filter_in_params(self, filters: dict[str, list[str]]) -> dict[str, str]:
        """Build ``__in`` filter parameters for multi-field filtering."""
        return build_filter_in_params(filters)

    def _normalize_filter_field(self, entity_type: str, filter_field: str) -> str:
        """Map Silver field names to ChEMBL API field names."""
        return normalize_filter_field(entity_type, filter_field)

    def _get_api_pk_field(self, entity_type: str) -> str:
        """Get primary key field name as it appears in raw API responses."""
        return get_api_pk_field(entity_type=entity_type, mapper=self._mapper)

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]:
        """Get dedup key fields as they appear in raw API responses."""
        return get_api_dedup_fields(entity_type=entity_type, mapper=self._mapper)

    def _build_filter_params(
        self, entity_type: str, filter_field: str, id_batch: list[str]
    ) -> dict[str, str]:
        """Build filter params using API-specific field names."""
        return build_filter_params(
            entity_type=entity_type, filter_field=filter_field, id_batch=id_batch
        )

    def _get_projected_url_length(self, url: str, params: JsonDict) -> int:
        """Estimate length of the final URL with parameters."""
        return projected_url_length(url=url, params=params)

    def _compute_composite_key(
        self, record: BronzeRecord, pk_fields: tuple[str, ...]
    ) -> str:
        """Compute composite key string from multiple fields."""
        return compute_record_composite_key(record, pk_fields)

    def _is_duplicate_record(
        self,
        record: BronzeRecord,
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate and add to seen set if not."""
        return check_duplicate_record(
            record=record,
            pk_field=pk_field,
            seen_ids=seen_ids,
            entity_type=entity_type,
            logger=self._logger,
            adapter_metrics=self._adapter_metrics,
        )

    def _is_duplicate_record_composite(
        self,
        record: BronzeRecord,
        pk_fields: tuple[str, ...],
        seen_keys: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate using composite key."""
        return check_duplicate_composite(
            record=record,
            pk_fields=pk_fields,
            seen_keys=seen_keys,
            entity_type=entity_type,
            logger=self._logger,
            adapter_metrics=self._adapter_metrics,
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
        """Fetch ChEMBL records as typed DTO models."""
        async for model in iter_chembl_as_models(
            fetch_fn=self.fetch,
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            validate=validate,
        ):
            yield model

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities."""
        url = self._mapper.get_resource_url(entity_type)
        with self._adapter_metrics.measure_request(f"/{entity_type}/count"):
            response = await self.http_client.get(
                url, params={"limit": 1, "format": "json"}
            )
        return int(response.json().get("page_meta", {}).get("total_count", 0))
