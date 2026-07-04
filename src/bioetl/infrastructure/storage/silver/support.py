"""Support utilities for Silver layer operations."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError

from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.delta.schema_ops import (
    delta_schema_to_pyarrow,
    drop_nondeterministic_persisted_fields,
)
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
    resolve_delta_table_path,
)

__all__ = [
    "get_table_schema",
    "prepare_arrow_data",
    "resolve_table_path",
]

# Create a shared ArrowDataConverter instance for the prepare_arrow_data function
_arrow_converter = ArrowDataConverter()


def resolve_table_path(
    base_path: str | Path, table_name: str, flat_structure: bool = False
) -> str:
    """Resolve the filesystem path for a Delta table.

    Args:
        base_path: Base path for Delta tables.
        table_name: Table name in dot notation (e.g., 'chembl.activity').
        flat_structure: If True, returns base_path directly.

    Returns:
        String path to the table directory.
    """
    return resolve_delta_table_path(
        base_path=str(base_path),
        table_name=table_name,
        flat_structure=flat_structure,
    )


async def get_table_schema(base_path: str | Path, table_name: str) -> pa.Schema | None:
    """Get existing table schema if table exists.

    Retrieves the PyArrow schema from an existing Delta table.
    Used for schema evolution checks and validation.

    Args:
        base_path: Base path for Delta tables.
        table_name: Table name in dot notation (e.g., 'chembl.activity').

    Returns:
        PyArrow Schema if table exists, None otherwise.
    """
    table_path = resolve_table_path(base_path, table_name)

    def _sync_get_schema() -> pa.Schema | None:
        try:
            # Load the Delta table
            dt = DeltaTable(normalize_delta_filesystem_path(table_path))
            return delta_schema_to_pyarrow(dt.schema())
        except TableNotFoundError:
            return None
        except Exception:
            # Handle other potential errors (permission issues, corrupt tables, etc.)
            return None

    # Run the synchronous DeltaTable loading in an executor to avoid blocking
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_get_schema)


def prepare_arrow_data(
    records: list[dict[str, object]],
    schema: pa.Schema,
    primary_keys: list[str],
    column_order: list[str] | None = None,
) -> pa.Table:
    """Prepare Arrow table from records with schema filtering and sorting.

    This is a standalone version of the method from SilverWriterArrowMixin.

    Args:
        records: List of record dictionaries to convert.
        schema: PyArrow schema defining target field types.
        primary_keys: List of column names used for ascending sort order.
        column_order: Optional explicit column ordering; uses canonical order if None.

    Returns:
        PyArrow Table filtered to schema columns, ordered, and sorted by primary keys.
    """
    # Convert records to Arrow table using the shared converter
    arrow_table = _arrow_converter.convert_records_to_arrow_with_schema(
        records,
        schema,
        primary_keys=primary_keys,
        column_order=column_order,
    )

    # Apply schema filtering to drop nondeterministic persisted fields
    filtered_table = drop_nondeterministic_persisted_fields(arrow_table)

    return filtered_table
