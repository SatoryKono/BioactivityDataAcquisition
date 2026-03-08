"""ChEMBL data source adapter implementing DataSourcePort.

Health-aware fetching: HEALTHY=full batch, DEGRADED=batch/2, UNHEALTHY=fail fast.
"""

from __future__ import annotations

__all__ = ["ChemblAdapter"]

import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.chembl.constants import (
    _NO_PAGINATION_ENTITIES,
    _SILVER_TO_CHEMBL_API_FIELD,
    CHEMBL_DTO_MODELS,
)
from bioetl.infrastructure.adapters.chembl.deduplication import (
    compute_composite_key,
    is_duplicate_record,
    is_duplicate_record_composite,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import (
    ChemblEntityMapper,
)
from bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin import (
    ChemblFetchAdapterMixin,
)
from bioetl.infrastructure.adapters.chembl.health import ChemblHealthMixin
from bioetl.infrastructure.adapters.chembl.metadata import ChemblMetadataMixin
from bioetl.infrastructure.adapters.error_handling import ErrorService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
        FallbackFetchOrchestratorService,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass
class ChemblAdapter(
    ChemblFetchAdapterMixin, ChemblHealthMixin, ChemblMetadataMixin, BaseHttpAdapter
):
    """ChEMBL REST adapter with pagination, filtering, and resilience helpers."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    adapter_config: AdapterConfig | None = None
    thread_pool: ThreadPoolExecutor | None = None
    metrics: MetricsPort | None = None
    extraction_params: ExtractionParams | None = None
    error_handler: ErrorHandlerPort | None = None
    adapter_metrics: AdapterMetrics | None = None
    request_collector: APIRequestCollector | None = None
    fallback_fetch_service: FallbackFetchOrchestratorService | None = None

    provider_name: str = field(init=False, default="chembl")

    _page_size: int = field(init=False, default=1000)
    _filter_batch_size: int = field(init=False, default=20)
    _mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)
    _extraction_params: ExtractionParams = field(
        init=False, default_factory=ExtractionParams.empty
    )

    def __post_init__(self) -> None:
        """Initialize adapter with config values and metrics."""
        # Initialize error handler: use injected or create fallback
        if self.error_handler is not None:
            self._error_handler = self.error_handler
        else:
            metrics_port = self.metrics if self.metrics is not None else None
            self._error_handler = ErrorService(self.logger, metrics=metrics_port)
        # Resolve configuration: use provided config or domain defaults
        config = (
            self.adapter_config if self.adapter_config is not None else AdapterConfig()
        )
        self._page_size = config.page_size
        self._filter_batch_size = config.batch_size

        if self.adapter_metrics is not None and self.request_collector is not None:
            self._adapter_metrics = self.adapter_metrics
            self._request_collector = self.request_collector
        else:
            self._init_adapter_metrics()

        # Resolve extraction params
        self._extraction_params = self.extraction_params or ExtractionParams.empty()

        if not self._extraction_params.is_empty:
            self.logger.info(
                "chembl_extraction_params_configured",
                provider="chembl",
                param_count=len(self._extraction_params.params),
                query_string=self._extraction_params.to_query_string(),
            )

    @property
    def effective_batch_size(self) -> int:
        """Get configured page size for API requests."""
        return self._page_size

    def _build_params(
        self, offset: int, entity_type: str | None = None
    ) -> JsonDict:  # Any: HTTP query params (str|int|bool values)
        """Build API request parameters with health-aware batch size.

        Args:
            offset: Pagination offset to include in the request parameters.
            entity_type: Entity type name; some entities skip limit/offset pagination.

        Returns:
            Dictionary of query parameters for the API request.
        """
        params: JsonDict = {  # Any: untyped API JSON record
            "format": "json"
        }  # Any: HTTP query params (str|int|bool values)

        # Some endpoints don't support limit/offset pagination
        if entity_type not in _NO_PAGINATION_ENTITIES:
            params["limit"] = self._get_effective_batch_size()
            params["offset"] = offset

        # Extraction-level filtering (ADR-028 §3)
        if not self._extraction_params.is_empty:
            params.update(self._extraction_params.to_query_dict())

        return params

    def _process_response(
        self, response: Response, entity_type: str
    ) -> tuple[list[BronzeRecord], bool]:
        """Process API response and return records with pagination flag.

        Args:
            response: HTTP response from the ChEMBL API.
            entity_type: Entity type being fetched (e.g. "compound", "activity").

        Returns:
            Tuple of (list of extracted records, whether there is a next page).
        """
        data = response.json()  # Any: untyped ChEMBL API JSON response
        plural_key = self._mapper.get_plural_key(entity_type)
        records = data.get(plural_key, [])
        if entity_type in {"publication", "publication_term"}:
            for record in records:
                if "publication_id" not in record and record.get("document_chembl_id"):
                    record["publication_id"] = record["document_chembl_id"]
        page_meta = data.get("page_meta", {})
        has_next = page_meta.get("next") is not None
        return records, has_next

    def _batch_ids(self, ids: list[str], batch_size: int) -> Iterator[list[str]]:
        """Split IDs into batches for API requests.

        Args:
            ids: Full list of IDs to split into batches.
            batch_size: Maximum number of IDs per batch.

        Returns:
            Iterator yielding successive sub-lists of size batch_size.
        """
        for i in range(0, len(ids), batch_size):
            yield ids[i : i + batch_size]

    def _build_filter_in_params(self, filters: dict[str, list[str]]) -> dict[str, str]:
        """Build ``__in`` filter parameters for multi-field filtering.

        Args:
            filters: Mapping of field name to list of IDs to filter by.

        Returns:
            Dictionary mapping field__in keys to comma-joined ID strings.
        """
        return {
            f"{filter_field}__in": ",".join(ids)
            for filter_field, ids in filters.items()
            if ids
        }

    def _normalize_filter_field(self, entity_type: str, filter_field: str) -> str:
        """Map Silver field names to ChEMBL API field names.

        Args:
            entity_type: Entity type being processed (unused, for interface consistency).
            filter_field: Silver layer field name to translate to API field name.

        Returns:
            ChEMBL API field name corresponding to the Silver layer field name.
        """
        return _SILVER_TO_CHEMBL_API_FIELD.get(filter_field, filter_field)

    def _get_api_pk_field(self, entity_type: str) -> str:
        """Get primary key field name as it appears in raw API responses.

        Args:
            entity_type: Entity type to look up the primary key field for.

        Returns:
            API-level primary key field name string.
        """
        pk = self._mapper.get_primary_key_field(entity_type)
        return _SILVER_TO_CHEMBL_API_FIELD.get(pk, pk)

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]:
        """Get dedup key fields as they appear in raw API responses.

        Args:
            entity_type: Entity type to look up deduplication key fields for.

        Returns:
            Tuple of API-level field name strings used for deduplication.
        """
        fields = self._mapper.get_dedup_key_fields(entity_type)
        return tuple(_SILVER_TO_CHEMBL_API_FIELD.get(f, f) for f in fields)

    def _build_filter_params(
        self, entity_type: str, filter_field: str, id_batch: list[str]
    ) -> dict[str, str]:
        """Build filter params using API-specific field names.

        Args:
            entity_type: Entity type to resolve the API field name for.
            filter_field: Silver layer field name to translate and filter by.
            id_batch: Batch of IDs to include in the __in filter.

        Returns:
            Dictionary with the __in filter parameter for the API request.
        """
        joined_ids = ",".join(id_batch)
        api_filter_field = self._normalize_filter_field(entity_type, filter_field)
        return {f"{api_filter_field}__in": joined_ids}

    def _get_projected_url_length(
        self,
        url: str,
        params: JsonDict,  # Any: untyped API JSON record
    ) -> int:  # Any: HTTP query params (str|int|bool values)
        """Estimate length of the final URL with parameters.

        Args:
            url: Base URL without query string.
            params: Query parameters to URL-encode and append.

        Returns:
            Number of characters in the URL-encoded request URL including query string.
        """
        # URL-encode parameters to get accurate length (including escaping)
        query_str = urllib.parse.urlencode(params, doseq=True)
        return len(url) + 1 + len(query_str)

    def _compute_composite_key(
        self,
        record: BronzeRecord,
        pk_fields: tuple[str, ...],
    ) -> str:
        """Compute composite key string from multiple fields.

        Args:
            record: Bronze record dictionary to extract key fields from.
            pk_fields: Tuple of field names whose values form the composite key.

        Returns:
            Composite key string with field values joined by '|'.
        """
        return compute_composite_key(record, pk_fields)

    def _is_duplicate_record(
        self,
        record: BronzeRecord,
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate and add to seen set if not.

        Args:
            record: Bronze record to check for duplication.
            pk_field: Primary key field name to extract from the record.
            seen_ids: Mutable set of already-seen primary key values.
            entity_type: Entity type used for logging context.

        Returns:
            True if the record is a duplicate, False if it is new.
        """
        return is_duplicate_record(
            record, pk_field, seen_ids, entity_type, self.logger, self._adapter_metrics
        )

    def _is_duplicate_record_composite(
        self,
        record: BronzeRecord,
        pk_fields: tuple[str, ...],
        seen_keys: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate using composite key.

        Args:
            record: Bronze record to check for duplication.
            pk_fields: Tuple of field names that form the composite key.
            seen_keys: Mutable set of already-seen composite key strings.
            entity_type: Entity type used for logging context.

        Returns:
            True if the composite key has been seen before, False if it is new.
        """
        return is_duplicate_record_composite(
            record,
            pk_fields,
            seen_keys,
            entity_type,
            self.logger,
            self._adapter_metrics,
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
        """Fetch ChEMBL records as typed DTO models.

        Args:
            entity_type: Entity type to fetch (e.g. "compound", "activity").
            limit: Maximum number of records to return, or None for all.
            query: Optional free-text query string for the API.
            filter_ids: Optional list of IDs to filter results by.
            filter_field: Field name to use for ID filtering.
            validate: If True, uses strict Pydantic validation; if False, uses fast model_construct.

        Yields:
            Typed Pydantic model instances for each fetched record.

        Raises:
            ValueError: If no DTO model is registered for the given entity_type.
        """
        model_class = CHEMBL_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(
                f"No DTO model for entity_type '{entity_type}'. "
                f"Supported: {', '.join(CHEMBL_DTO_MODELS.keys())}"
            )

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            if validate:
                # Strict validation - will raise on unknown fields
                yield model_class.model_validate(record)
            else:
                # Fast path - skip validation for trusted data
                yield model_class.model_construct(**record)

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities.

        Args:
            entity_type: Entity type to count (e.g. "compound", "activity").

        Returns:
            Number of entities of the specified type in the ChEMBL database.
        """
        url = self._mapper.get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}
        with self._adapter_metrics.measure_request(f"/{entity_type}/count"):
            response = await self.http_client.get(url, params=params)
        data = response.json()
        page_meta = data.get("page_meta", {})
        total_count: int = page_meta.get("total_count", 0)
        return total_count
