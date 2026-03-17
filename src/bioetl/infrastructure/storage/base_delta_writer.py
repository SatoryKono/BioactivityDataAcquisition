"""Base class for Delta Lake writers.

Provides common functionality for Silver and Gold Delta Lake writers,
including Arrow data preparation, schema handling, and table management.

Implements shared infrastructure for RULES.md §2.1 Medallion Architecture:
- Arrow table preparation with schema-aware filtering delegated to ArrowDataConverter
- Primary key sorting for deterministic writes (ADR-014)
- Table path management
- Clear/cleanup operations

This module extracts common code from SilverWriter and GoldWriter
to follow DRY principle and simplify maintenance.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.arrow_converter import (
    ArrowDataConverter,
)
from bioetl.infrastructure.storage.arrow_converter import (
    get_string_fields as _get_string_fields_impl,
)
from bioetl.infrastructure.storage.arrow_converter import (
    serialize_value_for_arrow_schema as _serialize_value_impl,
)
from bioetl.infrastructure.storage.arrow_converter import (
    sort_arrow_table_by_primary_keys as _sort_by_primary_keys_impl,
)
from bioetl.infrastructure.storage.delta_schema_ops import (
    coerce_null_types_for_delta as _coerce_null_types_for_delta_impl,
)
from bioetl.infrastructure.storage.delta_table_ops import (
    clear_delta_tables as _clear_delta_tables_impl,
)
from bioetl.infrastructure.storage.delta_table_ops import (
    get_delta_table_arrow_schema as _get_delta_table_arrow_schema_impl,
)
from bioetl.infrastructure.storage.delta_table_ops import (
    read_delta_records as _read_delta_records_impl,
)
from bioetl.infrastructure.storage.delta_table_ops import (
    resolve_delta_table_path as _resolve_delta_table_path_impl,
)
from bioetl.infrastructure.storage.retention_manager import RetentionPolicy

__all__ = ["BaseDeltaWriter", "coerce_null_types_for_delta"]

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.ports import LoggerPort


# Any: arbitrary Python value from heterogeneous record fields; returns same or JSON string
def _serialize_value(
    value: Any,  # Any: Arrow field value type varies
    is_string_field: bool,  # Any: Arrow field value type varies
) -> Any:  # Any: input/output type varies
    """Compatibility wrapper delegating schema-aware serialization to Arrow converter."""
    return _serialize_value_impl(value, is_string_field)


def _get_string_fields(schema: pa.Schema) -> set[str]:
    """Compatibility wrapper delegating schema inspection to Arrow converter."""
    return _get_string_fields_impl(schema)


def _read_delta_records(
    table: DeltaTable,
    columns: list[str] | None = None,
) -> list[BronzeRecord]:
    """Read Delta rows into generic record dictionaries."""
    return _read_delta_records_impl(table, columns)


def _load_delta_table(table_path: str) -> DeltaTable:
    """Open a Delta table from its resolved filesystem path."""
    return DeltaTable(table_path)


def _resolve_delta_table_path(
    *,
    base_path: str,
    table_name: str,
    flat_structure: bool,
) -> str:
    """Resolve the filesystem path for a Delta table."""
    return _resolve_delta_table_path_impl(
        base_path=base_path,
        table_name=table_name,
        flat_structure=flat_structure,
    )


def _get_delta_table_arrow_schema(table: DeltaTable) -> pa.Schema:
    """Extract the PyArrow schema from an opened Delta table."""
    return _get_delta_table_arrow_schema_impl(table)


def _clear_delta_tables(
    *,
    base_path: Path,
    table_path: Path | None,
    dry_run: bool,
) -> int:
    """Clear one Delta table or all Delta tables rooted at a base path."""
    return _clear_delta_tables_impl(
        base_path=base_path,
        table_path=table_path,
        dry_run=dry_run,
    )


def coerce_null_types_for_delta(table: pa.Table) -> pa.Table:
    """Coerce Null-typed columns to concrete types for Delta Lake compatibility.

    Delta Lake doesn't support Null type in any form:
    - Top-level null columns (all values are None) -> String
    - List columns with null item type (list<item: null>) -> List<String>

    This function modifies the table schema to use concrete types while
    preserving the null values.

    Args:
        table: PyArrow Table that may have Null-typed columns.

    Returns:
        PyArrow Table with Null columns coerced to String types.

    Example:
        >>> records = [{'id': '1', 'empty_list': [], 'null_col': None}]
        >>> table = pa.Table.from_pylist(records)
        >>> table.schema  # list<item: null>, null
        >>> fixed = coerce_null_types_for_delta(table)
        >>> fixed.schema  # list<item: string>, string
    """
    return _coerce_null_types_for_delta_impl(table)


class BaseDeltaWriter:
    """Base class with common functionality for Delta Lake writers.

    Provides shared infrastructure for Silver and Gold writers:
    - Arrow data preparation with schema filtering and serialization
    - Primary key sorting for deterministic writes (ADR-014)
    - Table schema retrieval and path management
    - Clear/cleanup operations for maintenance

    Subclasses (SilverWriter, GoldWriter) inherit this functionality
    and implement layer-specific write modes and merge strategies.

    Attributes:
        base_path: Base filesystem path for Delta tables.
        logger: Structured logger for observability.

    Example:
        >>> class MyWriter(BaseDeltaWriter):
        ...     async def write(self, records, schema):
        ...         arrow_table = self._prepare_arrow_data(records, schema, ["id"])
        ...         # Write arrow_table to Delta...
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
    ) -> None:
        """Initialize base Delta writer.

        Args:
            base_path: Base path for Delta table storage.
                      Tables are stored as subdirectories (e.g., base_path/chembl/activity/).
            logger: Structured logger for observability (MUST be injected per RULES.md).
            flat_structure: If True, Delta data is written directly to base_path
                          without creating table_name subdirectory.
        """
        self.base_path = str(base_path).rstrip("/")
        self.logger = logger
        self._flat_structure = flat_structure
        self._arrow_converter = ArrowDataConverter(logger=logger)
        self._retention_manager = RetentionPolicy(base_path)

    def _resolve_table_path(self, table_name: str) -> str:
        """Resolve the filesystem path for a Delta table.

        In flat_structure mode, returns base_path directly.
        Otherwise, appends table_name as subdirectory.

        Args:
            table_name: Table name in dot notation (e.g., 'chembl.activity').

        Returns:
            String path to the table directory.
        """
        return _resolve_delta_table_path(
            base_path=self.base_path,
            table_name=table_name,
            flat_structure=self._flat_structure,
        )

    def _prepare_arrow_data(
        self,
        records: list[BronzeRecord],
        schema: pa.Schema,
        primary_keys: list[str],
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting.

        Performs the following transformations:
        1. Filters record fields to match schema (drops unknown fields)
        2. Serializes complex types (dict, list) to JSON for string fields
        3. Sorts by primary keys for deterministic writes (ADR-014)

        Args:
            records: List of record dictionaries to convert.
            schema: PyArrow schema defining target field types.
            primary_keys: List of field names to sort by.

        Returns:
            PyArrow Table with filtered, serialized, and sorted data.
        """
        return self._arrow_converter.convert_records_to_arrow_with_schema(
            records,
            schema,
            primary_keys=primary_keys,
        )

    def _sort_by_primary_keys(
        self,
        table: pa.Table,
        primary_keys: list[str],
        schema_names: Sequence[str],
    ) -> pa.Table:
        """Sort Arrow table by primary keys for deterministic writes.

        Ensures consistent row ordering across writes for reproducibility
        per ADR-014 deterministic writes requirement.

        Args:
            table: PyArrow Table to sort.
            primary_keys: List of field names to sort by (in order).
            schema_names: Available field names in the schema.

        Returns:
            Sorted PyArrow Table, or original table if no valid keys found.

        Note:
            Logs a warning if specified primary keys are not in schema.
        """
        return _sort_by_primary_keys_impl(
            table,
            primary_keys,
            schema_names=schema_names,
            logger=self.logger,
        )

    async def _open_delta_table(self, table_name: str) -> DeltaTable | None:
        """Open one Delta table by name and return None when it is missing."""
        table_path = self._resolve_table_path(table_name)
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _load_delta_table, table_path)
        except DeltaTableNotFoundError:
            return None

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get existing table schema if table exists.

        Retrieves the PyArrow schema from an existing Delta table.
        Used for schema evolution checks and validation.

        Args:
            table_name: Table name in dot notation (e.g., 'chembl.activity').

        Returns:
            PyArrow Schema if table exists, None otherwise.
        """
        dt = await self._open_delta_table(table_name)
        if dt is None:
            return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _get_delta_table_arrow_schema, dt)

    def get_table_path(self, table_name: str) -> Path:
        """Get the filesystem path for a Delta table.

        Converts dot-notation table names to filesystem paths.
        In flat_structure mode, returns base_path directly.

        Args:
            table_name: Table name in dot notation (e.g., 'chembl.activity').

        Returns:
            Path object pointing to the table directory.

        Example:
            >>> writer = BaseDeltaWriter("/data/silver", logger)
            >>> writer.get_table_path("chembl.activity")
            PosixPath('/data/silver/chembl/activity')
        """
        from pathlib import Path

        return Path(self._resolve_table_path(table_name))

    async def read_table(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:  # BronzeRecord: generic record dict from Delta table
        """Read records from a Delta table.

        Args:
            table_name: Table name in dot notation (e.g., 'chembl.activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        dt = await self._open_delta_table(table_name)
        if dt is None:
            raise FileNotFoundError(f"Table not found: {table_name}")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read_delta_records, dt, columns)

    def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
        """Clear Delta table(s) by removing their directories.

        Removes table data and Delta log. Used for rebuild operations
        and cleanup. Identifies Delta tables by presence of _delta_log directory.

        Args:
            table_name: Specific table to clear (dot notation).
                       If None, clears all Delta tables in base_path.
            dry_run: If True, only count tables without removing them.

        Returns:
            Number of tables cleared (or would be cleared in dry_run mode).

        Warning:
            This operation is destructive and cannot be undone.
            Used primarily for rebuild runs per RULES.md §2.1.
        """
        from pathlib import Path

        base = Path(self.base_path)
        return _clear_delta_tables(
            base_path=base,
            table_path=self.get_table_path(table_name) if table_name else None,
            dry_run=dry_run,
        )
