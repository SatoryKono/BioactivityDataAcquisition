"""Table shaping operations for CSV exporter."""

from __future__ import annotations

from builtins import __import__ as _builtin_import
from typing import TYPE_CHECKING

import pyarrow as pa

from bioetl.domain.serialization import serialize_to_json

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def is_complex_type(field_type: pa.DataType) -> bool:
    """Check if a PyArrow type is complex (list or struct)."""
    return bool(
        pa.types.is_list(field_type)
        or pa.types.is_large_list(field_type)
        or pa.types.is_struct(field_type)
    )


def serialize_column_to_json(col: pa.ChunkedArray) -> pa.Array:
    """Serialize a column of complex values to JSON strings."""
    vals = [
        serialize_to_json(value) if value is not None else None
        for value in col.to_pylist()
    ]
    return pa.array(vals, type=pa.string())


def flatten_table_for_csv(table: pa.Table) -> pa.Table:
    """Convert complex types (list, struct) to JSON strings for CSV export."""
    complex_flags = tuple(is_complex_type(field.type) for field in table.schema)
    if not any(complex_flags):
        return table

    new_columns = []
    for i, _field in enumerate(table.schema):
        col = table.column(i)
        if complex_flags[i]:
            new_columns.append(serialize_column_to_json(col))
        else:
            new_columns.append(col)

    new_schema = pa.schema(
        [
            pa.field(
                field.name,
                pa.string() if complex_flags[i] else field.type,
                field.nullable,
            )
            for i, field in enumerate(table.schema)
        ]
    )
    return pa.Table.from_arrays(new_columns, schema=new_schema)


def sort_table(
    table: pa.Table,
    sort_columns: list[str],
    *,
    sort_ascending: bool,
) -> pa.Table:
    """Sort table by specified columns for deterministic output."""
    if not sort_columns:
        return table

    existing_cols = [column for column in sort_columns if column in table.schema.names]
    if not existing_cols:
        return table

    direction = "ascending" if sort_ascending else "descending"
    sort_keys = [(column, direction) for column in existing_cols]
    return table.sort_by(sort_keys)


def deduplicate_table(
    table: pa.Table,
    primary_keys: list[str],
    *,
    logger: LoggerPort,
) -> pa.Table:
    """Deduplicate table based on primary keys."""
    if not primary_keys:
        return table
    if table.num_rows < 2:
        return table

    missing_keys = [key for key in primary_keys if key not in table.column_names]
    if missing_keys:
        logger.warning(
            "Cannot deduplicate CSV: missing primary keys",
            missing_keys=missing_keys,
        )
        return table

    try:
        pl = _builtin_import("polars")
        df = pl.from_arrow(table)
        original_count = df.height
        # OPTIMIZATION: maintain_order=False avoids high FFI overhead for large cardinality data.
        # We explicitly sort afterwards to ensure deterministic output.
        df = df.unique(
            subset=primary_keys,
            keep="last",
            maintain_order=False,
        ).sort(primary_keys)
        dedup_count = df.height

        if dedup_count < original_count:
            logger.debug(
                "Deduplicated CSV data",
                removed_rows=original_count - dedup_count,
            )

        return df.to_arrow()
    except ImportError:
        logger.warning("Polars not available for CSV deduplication")
        return table
    except (
        pa.ArrowException,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RuntimeError,
    ) as exc:
        logger.warning("CSV deduplication failed", error=str(exc))
        return table
