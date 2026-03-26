"""Shared pure helpers for composite metadata parsing and assembly.

The helpers in this module are intentionally I/O-free and can be consumed
from both application and infrastructure layers without violating
layer boundaries.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast

from bioetl.domain.composite.lineage import (
    CompositeLineageMetadata,
    EnrichmentStatusRecord,
)
from bioetl.domain.models.metadata import (
    CompositeOutputExt,
    CompositeSchemaValidationMetadata,
)
from bioetl.domain.services.composite_metadata_cv import summarize_composite_cv_dq

__all__ = [
    "extract_composite_lineage_metadata",
    "extract_composite_output_ext",
    "parse_composite_field_sources",
    "parse_composite_list",
    "parse_composite_status",
    "parse_lineage_created_at",
    "summarize_composite_cv_dq",
]


def _parse_literal(value: object) -> object | None:
    """Parse a Python literal from string payload, returning None on failure."""
    if not isinstance(value, str):
        return None
    try:
        return cast("object", ast.literal_eval(value))
    except (ValueError, SyntaxError):
        return None


def _normalize_composite_list(value: object) -> list[str]:
    """Normalize list-like payload into ``list[str]``."""
    return [str(item) for item in value] if isinstance(value, list) else []


def _normalize_composite_status(value: object) -> dict[str, str]:
    """Normalize dict-like payload into ``dict[str, str]``."""
    return (
        {str(key): str(item) for key, item in value.items()}
        if isinstance(value, dict)
        else {}
    )


def _normalize_composite_field_sources(value: object) -> dict[str, str]:
    """Normalize field-source payload into ``dict[str, str]``."""
    return (
        {str(key): str(item) for key, item in value.items()}
        if isinstance(value, dict)
        else {}
    )


def _has_composite_lineage_fields(sample: Mapping[str, object]) -> bool:
    """Return True when composite or lineage metadata fields are present."""
    has_composite_fields = any(key.startswith("_composite_") for key in sample)
    has_lineage_fields = "_source_providers" in sample or "_enrichment_status" in sample
    return has_composite_fields or has_lineage_fields


def _has_composite_graph_fields(sample: Mapping[str, object]) -> bool:
    """Return True when any graph-relevant composite fields are present."""
    return _has_composite_lineage_fields(sample) or any(
        field in sample
        for field in (
            "_field_sources",
            "_seed_record_id",
            "_enrichment_timestamps",
            "_cv_warn",
            "_cv_error",
            "_cv_quarantine",
        )
    )


def _normalize_optional_str(value: object) -> str | None:
    """Convert non-null payload into string value."""
    return str(value) if value is not None else None


def _build_schema_validation_metadata(
    *,
    enabled: bool,
    strict: bool | None,
) -> CompositeSchemaValidationMetadata:
    """Build schema validation metadata for composite output extension."""
    return CompositeSchemaValidationMetadata(
        enabled=enabled,
        strict=strict,
        status="passed" if enabled else "not_run",
    )


def _build_composite_output_ext(
    *,
    sample: Mapping[str, object],
    partition_count: int | None,
    schema_validation: CompositeSchemaValidationMetadata,
) -> CompositeOutputExt:
    """Build ``CompositeOutputExt`` from normalized sample payload."""
    if partition_count is None:
        return CompositeOutputExt(
            composite_run_id=_normalize_optional_str(sample.get("_composite_run_id")),
            source_providers=parse_composite_list(sample.get("_source_providers")),
            enrichment_status=parse_composite_status(sample.get("_enrichment_status")),
            lineage_created_at=parse_lineage_created_at(
                sample.get("_lineage_created_at")
            ),
            schema_validation=schema_validation,
        )
    return CompositeOutputExt(
        partition_count=partition_count,
        composite_run_id=_normalize_optional_str(sample.get("_composite_run_id")),
        source_providers=parse_composite_list(sample.get("_source_providers")),
        enrichment_status=parse_composite_status(sample.get("_enrichment_status")),
        lineage_created_at=parse_lineage_created_at(sample.get("_lineage_created_at")),
        schema_validation=schema_validation,
    )


def _build_enrichment_status_records(
    raw_status: Mapping[str, str],
) -> dict[str, EnrichmentStatusRecord]:
    """Convert plain status mapping into canonical enrichment records."""
    return {
        provider: EnrichmentStatusRecord(provider=provider, status=status)
        for provider, status in raw_status.items()
    }


def _resolve_composite_name(
    sample: Mapping[str, object],
    *,
    composite_name: str | None,
) -> str:
    """Resolve canonical composite name from record payload or caller fallback."""
    return (
        _normalize_optional_str(sample.get("_composite_name"))
        or composite_name
        or "composite"
    )


def _build_composite_lineage_metadata(
    *,
    sample: Mapping[str, object],
    composite_name: str | None,
) -> CompositeLineageMetadata:
    """Build canonical composite lineage metadata from one normalized sample."""
    raw_enrichment_status = parse_composite_status(sample.get("_enrichment_status"))
    return CompositeLineageMetadata(
        composite_run_id=_normalize_optional_str(sample.get("_composite_run_id")) or "",
        composite_name=_resolve_composite_name(
            sample,
            composite_name=composite_name,
        ),
        source_providers=tuple(parse_composite_list(sample.get("_source_providers"))),
        enrichment_status=_build_enrichment_status_records(raw_enrichment_status),
        field_sources=parse_composite_field_sources(sample.get("_field_sources")),
        seed_record_id=_normalize_optional_str(sample.get("_seed_record_id")),
        created_at=parse_lineage_created_at(sample.get("_lineage_created_at")),
    )


def parse_composite_list(value: object) -> list[str]:
    """Parse list metadata stored as list or stringified list."""
    parsed = value if isinstance(value, list) else _parse_literal(value)
    return _normalize_composite_list(parsed)


def parse_composite_status(value: object) -> dict[str, str]:
    """Parse status metadata stored as dict or stringified dict."""
    parsed = value if isinstance(value, dict) else _parse_literal(value)
    return _normalize_composite_status(parsed)


def parse_composite_field_sources(value: object) -> dict[str, str]:
    """Parse field-source metadata stored as dict or stringified dict."""
    parsed = value if isinstance(value, dict) else _parse_literal(value)
    return _normalize_composite_field_sources(parsed)


def parse_lineage_created_at(value: object) -> datetime | None:
    """Parse composite lineage timestamp from raw metadata payload."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def extract_composite_lineage_metadata(
    records: Sequence[Mapping[str, object]],
    *,
    composite_name: str | None = None,
) -> CompositeLineageMetadata | None:
    """Extract canonical composite lineage metadata from merged records.

    The returned object keeps the existing record-level composite hints queryable
    at the application layer without coupling graph assembly to Polars helpers.
    """
    if not records:
        return None

    sample = records[0]
    if not _has_composite_graph_fields(sample):
        return None

    return _build_composite_lineage_metadata(
        sample=sample,
        composite_name=composite_name,
    )


def extract_composite_output_ext(
    records: Sequence[Mapping[str, object]],
    *,
    partition_count: int | None = None,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output extension from merged records.

    Returns ``None`` when records are empty or when composite lineage fields
    are not present.
    """
    if not records:
        return None

    sample = records[0]
    if not _has_composite_lineage_fields(sample):
        return None

    return _build_composite_output_ext(
        sample=sample,
        partition_count=partition_count,
        schema_validation=_build_schema_validation_metadata(
            enabled=schema_validation_enabled,
            strict=schema_validation_strict,
        ),
    )
