"""Restore Delta partition columns omitted from physical Parquet files."""

from __future__ import annotations

from pathlib import Path


def read_partitioned_delta_file(
    path: Path,
    partition_values: dict[str, str | None],
    schema_json: str,
    columns: list[str] | None,
) -> object:
    """Use committed Delta values and types, including null partition values."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from deltalake import Schema
    from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow

    schema = delta_schema_to_pyarrow(Schema.from_json(schema_json))
    physical_columns = (
        [column for column in columns if column not in partition_values]
        if columns is not None
        else None
    )
    table = pq.read_table(path, columns=physical_columns, partitioning=None)
    for name, value in partition_values.items():
        if name in table.column_names or (columns is not None and name not in columns):
            continue
        typed = schema.field(name).type
        scalar = None if value is None or value == "" else value
        if scalar is None:
            column = pa.array([None] * table.num_rows, type=typed)
        else:
            column = pa.array([scalar] * table.num_rows).cast(typed)
        table = table.append_column(name, column)
    selected = list(columns) if columns is not None else list(schema.names)
    for field in schema:
        if field.name in table.column_names or field.name not in selected:
            continue
        if not field.nullable:
            continue
        table = table.append_column(
            field.name, pa.array([None] * table.num_rows, type=field.type)
        )
    return table.select(selected)
