"""Reusable Delta schema helper operations."""

from __future__ import annotations

import pyarrow as pa

from bioetl.domain.constants import NONDETERMINISTIC_PERSISTED_FIELDS


def delta_schema_to_pyarrow(delta_schema: object) -> pa.Schema:
    """Convert a delta-rs Schema to PyArrow across API renames."""
    for method_name in ("to_arrow", "to_pyarrow"):
        converter = getattr(delta_schema, method_name, None)
        if not callable(converter):
            continue
        schema = converter()
        if isinstance(schema, pa.Schema):
            return schema
        try:
            return pa.schema(schema)
        except (TypeError, ValueError, pa.ArrowException):
            continue
    raise TypeError(
        f"Unsupported delta schema type {type(delta_schema)!r}: "
        "expected to_arrow() or to_pyarrow()"
    )


def coerce_null_types_for_delta(table: pa.Table) -> pa.Table:
    """Coerce Null-typed columns to concrete types for Delta Lake compatibility."""
    for field in table.schema:
        if pa.types.is_null(field.type):
            col_idx = table.schema.get_field_index(field.name)
            null_array = pa.nulls(table.num_rows, type=pa.string())
            table = table.set_column(
                col_idx, pa.field(field.name, pa.string()), null_array
            )
        elif pa.types.is_list(field.type) and pa.types.is_null(field.type.value_type):
            col_idx = table.schema.get_field_index(field.name)
            empty_lists = pa.array(
                [[] for _ in range(table.num_rows)],
                type=pa.list_(pa.string()),
            )
            table = table.set_column(
                col_idx, pa.field(field.name, pa.list_(pa.string())), empty_lists
            )
    return table


def drop_nondeterministic_persisted_fields(table: pa.Table) -> pa.Table:
    """Drop occurrence-scoped provenance fields from persisted Delta rows.

    Runtime provenance remains available via explicit write kwargs, sidecars,
    run manifests, lineage fragments, and audit artifacts. This helper only
    affects the physical Silver/Gold dataset payload written to Delta.
    """

    removable = [
        column_name
        for column_name in table.column_names
        if column_name in NONDETERMINISTIC_PERSISTED_FIELDS
    ]
    if not removable:
        return table

    persisted_columns = [
        column_name
        for column_name in table.column_names
        if column_name not in NONDETERMINISTIC_PERSISTED_FIELDS
    ]
    return table.select(persisted_columns)
