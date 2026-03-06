"""Composite metadata parsing helpers for metadata builders."""

from __future__ import annotations

import ast
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import CompositeOutputExt


def parse_composite_list(value: object) -> list[str]:
    """Parse composite list metadata stored as list or stringified list.

    Returns:
        List of string items parsed from the input value, or empty list if unparseable.
    """
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def parse_composite_status(value: object) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict.

    Returns:
        Dictionary mapping string keys to string values, or empty dict if unparseable.
    """
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    return {}


def build_composite_output_ext(
    records: list[JsonDict],  # Any: record/metadata values are heterogeneous
) -> CompositeOutputExt | None:
    """Build CompositeOutputExt when composite lineage columns are present.

    Returns:
        CompositeOutputExt populated from record lineage columns, or None if records are empty
        or lack composite lineage fields.
    """
    from bioetl.domain.models.metadata import (
        CompositeOutputExt,
        CompositeSchemaValidationMetadata,
    )

    if not records:
        return None

    sample = records[0]
    has_composite_fields = any(key.startswith("_composite_") for key in sample)
    has_lineage_fields = "_source_providers" in sample or "_enrichment_status" in sample
    if not has_composite_fields and not has_lineage_fields:
        return None

    lineage_raw = sample.get("_lineage_created_at")
    lineage_created_at: datetime | None = None
    if isinstance(lineage_raw, str):
        try:
            lineage_created_at = datetime.fromisoformat(lineage_raw)
        except ValueError:
            lineage_created_at = None

    return CompositeOutputExt(
        composite_run_id=(
            str(sample.get("_composite_run_id"))
            if sample.get("_composite_run_id") is not None
            else None
        ),
        source_providers=parse_composite_list(sample.get("_source_providers")),
        enrichment_status=parse_composite_status(sample.get("_enrichment_status")),
        lineage_created_at=lineage_created_at,
        schema_validation=CompositeSchemaValidationMetadata(
            enabled=False,
            strict=None,
            status="not_run",
        ),
    )


__all__ = [
    "build_composite_output_ext",
    "parse_composite_list",
    "parse_composite_status",
]
