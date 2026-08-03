# Host attrs/methods provided by concrete composition.
"""Schema projection and resolution helpers for Gold writer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from bioetl.domain.types import GoldRecord, GoldSchemaPolicyByVersion
from bioetl.infrastructure.storage.gold.writer_protocols import (
    _ResolvedSchema,
    _SchemaBuilder,
)

__all__ = [
    "_project_records_for_gold_schema",
    "_resolve_active_gold_schema",
    "_schema_column_names",
]


def _schema_column_names(schema: object) -> tuple[str, ...]:
    """Extract ordered column names from a Pandera schema-like object."""
    if hasattr(schema, "to_schema"):
        try:
            resolved = cast(_ResolvedSchema, cast(_SchemaBuilder, schema).to_schema())
            return tuple(resolved.columns.keys())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass
    if hasattr(schema, "columns"):
        columns = cast(Any, schema).columns  # Any: schema columns duck-type
        if isinstance(columns, Mapping):
            return tuple(str(column) for column in columns)
    return ()


def _project_records_for_gold_schema(
    records: list[GoldRecord],
    *,
    schema: object,
) -> list[GoldRecord]:
    """Project raw Gold records to the ordered columns of one schema version."""
    schema_columns = _schema_column_names(schema)
    if not schema_columns:
        return records

    dq_defaults = {"_dq_warn": False, "_dq_error": False}
    return [
        {
            key: record.get(key, dq_defaults.get(key))
            for key in schema_columns
            if key in record or key in dq_defaults
        }
        for record in records
    ]


def _resolve_active_gold_schema(schema: object) -> object:
    """Return the active schema from version-aware routing or a plain schema."""
    if isinstance(schema, GoldSchemaPolicyByVersion):
        return schema.active_schema
    return schema
