"""Delta table loading helpers for retention operations."""

from __future__ import annotations

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import TableNotFoundError
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
    resolve_delta_table_path,
)


def get_table_path(base_path: str, table_name: str) -> str:
    """Get the filesystem path for a table."""
    return resolve_delta_table_path(
        base_path=base_path,
        table_name=table_name,
        flat_structure=False,
    )


def load_delta_table(table_path: str) -> DeltaTable:
    """Load a Delta table or translate the not-found error to the domain type."""
    try:
        return DeltaTable(normalize_delta_filesystem_path(table_path))
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc


def build_table_info(table: DeltaTable) -> JsonDict:
    """Build the normalized table-info payload from an open Delta table."""
    return {
        "version": table.version(),
        "num_files": len(table.file_uris()),
        "schema": delta_schema_to_pyarrow(table.schema()),
        "metadata": table.metadata(),
    }


__all__ = ["build_table_info", "get_table_path", "load_delta_table"]
