"""Delta table loading helpers for retention operations."""

from __future__ import annotations

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import TableNotFoundError
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow


def get_table_path(base_path: str, table_name: str) -> str:
    """Get the filesystem path for a table."""
    return f"{base_path}/{table_name.replace('.', '/')}"


def load_delta_table(table_path: str) -> DeltaTable:
    """Load a Delta table or translate the not-found error to the domain type."""
    try:
        return DeltaTable(table_path)
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
