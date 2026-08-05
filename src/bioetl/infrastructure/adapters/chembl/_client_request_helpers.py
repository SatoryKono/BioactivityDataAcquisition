"""Request-param and response helpers for ChemblAdapter."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from pydantic import BaseModel

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.chembl.constants import (
    CHEMBL_DTO_MODELS,
    _NO_PAGINATION_ENTITIES,
    _SILVER_TO_CHEMBL_API_FIELD,
)
from bioetl.infrastructure.adapters.chembl.deduplication import (
    compute_composite_key,
    is_duplicate_record,
    is_duplicate_record_composite,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from httpx import Response

    from bioetl.domain.models.filter import ExtractionParams
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper

__all__ = [
    "batch_ids",
    "build_filter_in_params",
    "build_filter_params",
    "build_request_params",
    "check_duplicate_composite",
    "check_duplicate_record",
    "compute_record_composite_key",
    "get_api_dedup_fields",
    "get_api_pk_field",
    "iter_chembl_as_models",
    "normalize_filter_field",
    "process_chembl_response",
    "projected_url_length",
    "resolve_chembl_dto_model",
]


def build_request_params(
    *,
    offset: int,
    entity_type: str | None,
    page_size: int,
    extraction_params: ExtractionParams,
) -> JsonDict:
    """Build API request parameters with health-aware batch size."""
    params: JsonDict = {"format": "json"}
    if entity_type not in _NO_PAGINATION_ENTITIES:
        params["limit"] = page_size
        params["offset"] = offset
    if not extraction_params.is_empty:
        params.update(extraction_params.to_query_dict())
    return params


def process_chembl_response(
    *,
    response: Response,
    entity_type: str,
    mapper: ChemblEntityMapper,
) -> tuple[list[BronzeRecord], bool]:
    """Process API response and return records with pagination flag."""
    data = response.json()
    plural_key = mapper.get_plural_key(entity_type)
    records = data.get(plural_key, [])
    if entity_type in {"publication", "publication_term"}:
        for record in records:
            if "publication_id" not in record and record.get("document_chembl_id"):
                record["publication_id"] = record["document_chembl_id"]
    page_meta = data.get("page_meta", {})
    has_next = page_meta.get("next") is not None
    return records, has_next


def batch_ids(ids: list[str], batch_size: int) -> Iterator[list[str]]:
    """Split IDs into batches for API requests."""
    for i in range(0, len(ids), batch_size):
        yield ids[i : i + batch_size]


def build_filter_in_params(filters: dict[str, list[str]]) -> dict[str, str]:
    """Build ``__in`` filter parameters for multi-field filtering."""
    return {
        f"{filter_field}__in": ",".join(ids)
        for filter_field, ids in filters.items()
        if ids
    }


def normalize_filter_field(entity_type: str, filter_field: str) -> str:
    """Map Silver field names to ChEMBL API field names."""
    _ = entity_type
    return _SILVER_TO_CHEMBL_API_FIELD.get(filter_field, filter_field)


def get_api_pk_field(*, entity_type: str, mapper: ChemblEntityMapper) -> str:
    """Get primary key field name as it appears in raw API responses."""
    pk = mapper.get_primary_key_field(entity_type)
    return _SILVER_TO_CHEMBL_API_FIELD.get(pk, pk)


def get_api_dedup_fields(
    *, entity_type: str, mapper: ChemblEntityMapper
) -> tuple[str, ...]:
    """Get dedup key fields as they appear in raw API responses."""
    fields = mapper.get_dedup_key_fields(entity_type)
    return tuple(_SILVER_TO_CHEMBL_API_FIELD.get(f, f) for f in fields)


def build_filter_params(
    *,
    entity_type: str,
    filter_field: str,
    id_batch: list[str],
) -> dict[str, str]:
    """Build filter params using API-specific field names."""
    joined_ids = ",".join(id_batch)
    api_filter_field = normalize_filter_field(entity_type, filter_field)
    return {f"{api_filter_field}__in": joined_ids}


def projected_url_length(*, url: str, params: JsonDict) -> int:
    """Estimate length of the final URL with parameters."""
    query_str = urlencode(params, doseq=True)
    return len(url) + 1 + len(query_str)


def compute_record_composite_key(
    record: BronzeRecord,
    pk_fields: tuple[str, ...],
) -> str:
    """Compute composite key string from multiple fields."""
    return compute_composite_key(record, pk_fields)


def check_duplicate_record(
    *,
    record: BronzeRecord,
    pk_field: str,
    seen_ids: set[str],
    entity_type: str,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
) -> bool:
    """Check if record is duplicate and add to seen set if not."""
    return is_duplicate_record(
        record, pk_field, seen_ids, entity_type, logger, adapter_metrics
    )


def check_duplicate_composite(
    *,
    record: BronzeRecord,
    pk_fields: tuple[str, ...],
    seen_keys: set[str],
    entity_type: str,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
) -> bool:
    """Check if record is duplicate using composite key."""
    return is_duplicate_record_composite(
        record,
        pk_fields,
        seen_keys,
        entity_type,
        logger,
        adapter_metrics,
    )


def resolve_chembl_dto_model(entity_type: str) -> type[BaseModel]:
    """Resolve DTO model class for a ChEMBL entity type."""
    model_class = CHEMBL_DTO_MODELS.get(entity_type)
    if model_class is None:
        raise ValueError(
            f"No DTO model for entity_type '{entity_type}'. "
            f"Supported: {', '.join(CHEMBL_DTO_MODELS.keys())}"
        )
    return model_class


async def iter_chembl_as_models(
    *,
    fetch_fn: Callable[..., AsyncIterator[BronzeRecord]],
    entity_type: str,
    limit: int | None,
    query: str | None,
    filter_ids: list[str] | None,
    filter_field: str | None,
    validate: bool,
) -> AsyncIterator[BaseModel]:
    """Yield ChEMBL records as typed DTO models."""
    model_class = resolve_chembl_dto_model(entity_type)
    async for record in fetch_fn(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    ):
        if validate:
            yield model_class.model_validate(record)
        else:
            yield model_class.model_construct(**record)



