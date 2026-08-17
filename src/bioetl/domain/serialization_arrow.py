"""Arrow-specific helpers for export-safe domain serialization."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pyarrow as pa


def flatten_arrow_table(table: pa.Table) -> pa.Table:
    """Convert complex Arrow columns to canonical JSON string columns."""
    import pyarrow as pa

    def is_complex_type(field_type: pa.DataType) -> bool:
        return bool(
            pa.types.is_list(field_type)
            or pa.types.is_large_list(field_type)
            or pa.types.is_struct(field_type)
        )

    def serialize_column(col: pa.ChunkedArray) -> pa.Array:
        values = [
            _serialize_arrow_value(value)
            if (value := scalar.as_py()) is not None
            else None
            for scalar in col
        ]
        return pa.array(values, type=pa.string())

    columns = [
        serialize_column(table.column(index))
        if is_complex_type(field.type)
        else table.column(index)
        for index, field in enumerate(table.schema)
    ]
    schema = pa.schema(
        [
            pa.field(
                field.name,
                pa.string() if is_complex_type(field.type) else field.type,
                field.nullable,
            )
            for field in table.schema
        ]
    )
    return pa.Table.from_arrays(columns, schema=schema)


def _serialize_arrow_value(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


__all__ = ["flatten_arrow_table"]
