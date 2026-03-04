"""ChEMBL data source adapter implementing DataSourcePort.

Health-aware fetching: HEALTHY=full batch, DEGRADED=batch/2, UNHEALTHY=fail fast.
"""

from __future__ import annotations

__all__ = ["ChemblAdapter"]


import urllib.parse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.resilience import AdapterConfig
from bioetl.domain.types import BronzeRecord
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

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass
class ChemblAdapter(
    ChemblFetchAdapterMixin, ChemblHealthMixin, ChemblMetadataMixin, BaseHttpAdapter
):
    """ChEMBL REST API adapter implementing DataSourcePort.

    Fetches bioactivity data from the EBI ChEMBL API at
    ``https://www.ebi.ac.uk/chembl/api/data``.

    Rate limiting:
        Token-bucket algorithm (3 req/s, burst 10) enforced by the
        injected ``UnifiedHTTPClient`` and its ``RateLimiterPort``.

    Pagination:
        Offset-based (``limit``/``offset`` query params, default page size
        1000). Entities listed in ``_NO_PAGINATION_ENTITIES``
        (target_component, protein_class) are fetched in a single request.
        For filtered queries, IDs are batched (default batch size 20) with
        ``__in`` filter syntax; URL length is capped at 1000 characters.

    Health-aware batch sizing (see ``ChemblHealthMixin``):
        * HEALTHY -- full ``page_size`` (default 1000).
        * DEGRADED -- ``max(100, page_size // 2)`` (halved, floor 100).
        * UNHEALTHY -- raises ``CriticalError`` immediately (fail-fast).

    Resilience:
        On ``RetryExhaustedError`` during filtered fetches the adapter
        splits the failing batch in half and retries each part recursively.
        Single-ID failures fall back to the direct-record endpoint
        (``/entity/CHEMBLID``) before logging a skip.

    Configuration (``configs/providers/chembl.yaml`` via ``AdapterConfig``):
        ``page_size`` (1000), ``batch_size`` (20), ``timeout_sec`` (60),
        ``max_retries`` (3), ``circuit_breaker.failure_threshold`` (5),
        ``circuit_breaker.recovery_timeout`` (300 s).
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    adapter_config: AdapterConfig | None = None
    thread_pool: ThreadPoolExecutor | None = None
    metrics: MetricsPort | None = None
    extraction_params: ExtractionParams | None = None

    provider_name: str = field(init=False, default="chembl")

    _page_size: int = field(init=False, default=1000)
    _filter_batch_size: int = field(init=False, default=20)
    _mapper: ChemblEntityMapper = field(init=False, default_factory=ChemblEntityMapper)
    _extraction_params: ExtractionParams = field(
        init=False, default_factory=ExtractionParams.empty
    )

    def __post_init__(self) -> None:
        """Initialize adapter with config values and metrics."""
        # Initialize error handler from base class
        self._error_handler = ErrorService(self.logger)
        # Resolve configuration: use provided config or domain defaults
        config = (
            self.adapter_config if self.adapter_config is not None else AdapterConfig()
        )
        self._page_size = config.page_size
        self._filter_batch_size = config.batch_size

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
    ) -> dict[str, Any]:  # Any: HTTP query params (str|int|bool values)
        """Build API request parameters with health-aware batch size.

        Args:
            offset: Pagination offset.
            entity_type: Entity type for determining pagination support.
                        If in _NO_PAGINATION_ENTITIES, limit/offset are excluded.

        Returns:
            Dictionary of query parameters.
        """
        params: dict[str, Any] = {  # Any: untyped API JSON record
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
        """Process API response, extract records and pagination info."""
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
        """Split IDs into batches for API requests."""
        for i in range(0, len(ids), batch_size):
            yield ids[i : i + batch_size]

    def _build_filter_in_params(self, filters: dict[str, list[str]]) -> dict[str, str]:
        """Build __in filter parameters for multi-field filtering."""
        return {
            f"{filter_field}__in": ",".join(ids)
            for filter_field, ids in filters.items()
            if ids
        }

    def _normalize_filter_field(self, entity_type: str, filter_field: str) -> str:
        """Map Silver field names to ChEMBL API field names."""
        return _SILVER_TO_CHEMBL_API_FIELD.get(filter_field, filter_field)

    def _get_api_pk_field(self, entity_type: str) -> str:
        """Get primary key field name as it appears in raw API responses."""
        pk = self._mapper.get_primary_key_field(entity_type)
        return _SILVER_TO_CHEMBL_API_FIELD.get(pk, pk)

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]:
        """Get dedup key fields as they appear in raw API responses."""
        fields = self._mapper.get_dedup_key_fields(entity_type)
        return tuple(_SILVER_TO_CHEMBL_API_FIELD.get(f, f) for f in fields)

    def _build_filter_params(
        self, entity_type: str, filter_field: str, id_batch: list[str]
    ) -> dict[str, str]:
        """Build filter params using API-specific field names."""
        joined_ids = ",".join(id_batch)
        api_filter_field = self._normalize_filter_field(entity_type, filter_field)
        return {f"{api_filter_field}__in": joined_ids}

    def _get_projected_url_length(
        self,
        url: str,
        params: dict[str, Any],  # Any: untyped API JSON record
    ) -> int:  # Any: HTTP query params (str|int|bool values)
        """Estimate the length of the final URL with parameters."""
        # URL-encode parameters to get accurate length (including escaping)
        query_str = urllib.parse.urlencode(params, doseq=True)
        return len(url) + 1 + len(query_str)

    def _compute_composite_key(
        self,
        record: BronzeRecord,
        pk_fields: tuple[str, ...],
    ) -> str:
        """Compute composite key string from multiple fields."""
        return compute_composite_key(record, pk_fields)

    def _is_duplicate_record(
        self,
        record: BronzeRecord,
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
    ) -> bool:
        """Check if record is duplicate and add to seen set if not."""
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
        """Check if record is duplicate using composite key."""
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
        """Fetch records from ChEMBL as typed DTO models.

        Returns Pydantic DTO models instead of raw dicts for type safety.
        Uses domain DTOs with extra='forbid' to detect API changes.

        Args:
            entity_type: Type of entity (activity, assay, molecule, target, etc.)
            limit: Maximum number of records to fetch
            query: Unused for ChEMBL
            filter_ids: List of IDs to filter by
            filter_field: Field name to filter on
            validate: If True, validate with model_validate (strict).
                     If False, use model_construct (skip validation, faster).

        Yields:
            Typed DTO models (ActivityRecord, AssayRecord, etc.)

        Raises:
            ValueError: If entity_type is not supported for DTO conversion
            ValidationError: If validate=True and API response has unexpected fields

        Example:
            >>> async for activity in adapter.fetch_as_models("activity", limit=100):
            ...     logger.debug("activity_fetched", activity_id=activity.activity_id, pchembl=activity.pchembl_value)

        Returns:
            Async iterator yielding fetched records.
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
            entity_type: Entity type identifier.

        Returns:
            Entity count.
        """
        url = self._mapper.get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}
        with self._adapter_metrics.measure_request(f"/{entity_type}/count"):
            response = await self.http_client.get(url, params=params)
        data = response.json()
        page_meta = data.get("page_meta", {})
        total_count: int = page_meta.get("total_count", 0)
        return total_count
