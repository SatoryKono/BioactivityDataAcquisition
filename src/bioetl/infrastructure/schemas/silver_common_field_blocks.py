"""Reusable field blocks for non-publication Silver schemas."""

from __future__ import annotations

import pyarrow as pa


def build_silver_system_prefix_fields(
    *,
    entity_id_nullable: bool = True,
    source_batch_nullable: bool = True,
    include_source: bool = False,
) -> list[pa.Field]:
    """Return the canonical Silver system-prefix block."""
    fields = [
        pa.field("entity_id", pa.string(), nullable=entity_id_nullable),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field(
            "_source_batch_id",
            pa.string(),
            nullable=source_batch_nullable,
        ),
    ]
    if include_source:
        fields.append(pa.field("_source", pa.string()))
    fields.extend(
        [
            pa.field("_ingestion_ts", pa.string()),
            pa.field("_index", pa.int64()),
        ]
    )
    return fields


def build_silver_lookup_prefix_fields() -> list[pa.Field]:
    """Return the shared lookup-prefix block used by publication-derived schemas."""
    return [
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
    ]


def build_silver_dq_suffix_fields() -> list[pa.Field]:
    """Return the canonical Silver DQ suffix block."""
    return [
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]


__all__ = [
    "build_silver_dq_suffix_fields",
    "build_silver_lookup_prefix_fields",
    "build_silver_system_prefix_fields",
]
