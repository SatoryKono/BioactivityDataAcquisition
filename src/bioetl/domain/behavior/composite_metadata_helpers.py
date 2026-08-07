"""Shared pure helpers for composite metadata parsing and assembly.

The helpers in this module are intentionally I/O-free and can be consumed
from both application and infrastructure layers without violating
layer boundaries.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast

from bioetl.domain.behavior.composite_metadata_cv import summarize_composite_cv_dq
from bioetl.domain.composite.lineage import CompositeLineageMetadata
from bioetl.domain.models.metadata import (
    CompositeOutputExt,
    CompositeSchemaValidationMetadata,
)

__all__ = [
    "extract_composite_lineage_metadata",
    "extract_composite_output_ext",
    "parse_composite_field_sources",
    "parse_composite_list",
    "parse_composite_status",
    "parse_lineage_created_at",
    "summarize_composite_cv_dq",
]

_LINEAGE_PAYLOAD_FIELDS = frozenset(
    {
        "_source_providers",
        "_enrichment_status",
        "_field_sources",
        "_lineage_created_at",
    }
)


def _parse_literal(value: object) -> object | None:
    """Parse a JSON literal from string payload with ast.literal_eval fallback."""
    if not isinstance(value, str):
        return None
    try:
        return cast("object", json.loads(value))
    except ValueError:
        # Fallback for legacy metadata using Python literals (single quotes)
        try:
            return cast("object", ast.literal_eval(value))
        except (ValueError, SyntaxError, MemoryError, TypeError, RecursionError):
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
    return any(key.startswith("_composite_") for key in sample) or bool(
        _LINEAGE_PAYLOAD_FIELDS.intersection(sample)
    )


def _normalize_composite_lineage_payload(
    sample: Mapping[str, object],
    *,
    composite_name: str,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> dict[str, object]:
    """Normalize legacy stringified lineage fields before VO reconstruction."""
    payload = dict(sample)
    payload.setdefault("_composite_name", composite_name)
    if composite_run_id is not None:
        payload["_composite_run_id"] = composite_run_id
    payload["_source_providers"] = parse_composite_list(
        payload.get("_source_providers")
    )
    payload["_enrichment_status"] = parse_composite_status(
        payload.get("_enrichment_status")
    )
    payload["_field_sources"] = parse_composite_field_sources(
        payload.get("_field_sources")
    )
    payload["_lineage_created_at"] = (
        lineage_created_at
        if lineage_created_at is not None
        else parse_lineage_created_at(payload.get("_lineage_created_at"))
    )
    return payload


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
    """Build CompositeOutputExt from normalized sample payload."""
    common = {
        "composite_run_id": _normalize_optional_str(sample.get("_composite_run_id")),
        "source_providers": parse_composite_list(sample.get("_source_providers")),
        "enrichment_status": parse_composite_status(sample.get("_enrichment_status")),
        "lineage_created_at": parse_lineage_created_at(
            sample.get("_lineage_created_at")
        ),
        "schema_validation": schema_validation,
    }
    if partition_count is not None:
        common["partition_count"] = partition_count
    return CompositeOutputExt(**common)



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


def extract_composite_output_ext(
    records: Sequence[Mapping[str, object]],
    *,
    partition_count: int | None = None,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output extension from merged records.

    Returns ``None`` when records are empty or when composite lineage fields
    are not present.
    """
    if not records:
        return None

    sample = dict(records[0])
    if composite_run_id is not None:
        sample["_composite_run_id"] = composite_run_id
    if lineage_created_at is not None:
        sample["_lineage_created_at"] = lineage_created_at.isoformat()
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


def extract_composite_lineage_metadata(
    records: Sequence[Mapping[str, object]],
    *,
    composite_name: str,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> CompositeLineageMetadata | None:
    """Extract one ``CompositeLineageMetadata`` payload from merged records.

    This compatibility façade reconstructs the lineage value object from the
    first record carrying composite metadata fields.
    """
    if not records:
        return None

    sample = dict(records[0])
    if composite_run_id is not None:
        sample["_composite_run_id"] = composite_run_id
    if lineage_created_at is not None:
        sample["_lineage_created_at"] = lineage_created_at.isoformat()
    if not _has_composite_lineage_fields(sample):
        return None

    return CompositeLineageMetadata.from_dict(
        _normalize_composite_lineage_payload(
            sample,
            composite_name=composite_name,
            composite_run_id=composite_run_id,
            lineage_created_at=lineage_created_at,
        )
    )
