"""Base class for Delta Lake writers.

Provides common functionality for Silver and Gold Delta Lake writers,
including Arrow data preparation, schema handling, and table management.

Implements shared infrastructure for RULES.md §2.1 Medallion Architecture:
- Arrow table preparation with schema filtering
- Primary key sorting for deterministic writes (ADR-014)
- Table path management
- Clear/cleanup operations

This module extracts common code from SilverWriter and GoldWriter
to follow DRY principle and simplify maintenance.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import orjson
import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.infrastructure.storage.retention_manager import RetentionManager

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.ports import LoggerPort


def _serialize_value(value: Any, is_string_field: bool) -> Any:
    """Serialize a value for Arrow storage.

    Converts complex Python types (dict, list) to JSON strings for string fields.
    This ensures proper storage in Delta Lake while preserving forensic data.

    Args:
        value: Value to serialize. Can be any Python type.
        is_string_field: True if the target Arrow field is a string type.

    Returns:
        Serialized value: JSON string for complex types in string fields,
        original value otherwise, or None if input is None.

    Example:
        >>> _serialize_value({"key": "val"}, is_string_field=True)
        '{"key":"val"}'
        >>> _serialize_value({"key": "val"}, is_string_field=False)
        {'key': 'val'}
        >>> _serialize_value(None, is_string_field=True)
        None
    """
    if value is None:
        return None
    if is_string_field and isinstance(value, (dict, list)):
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return value


def _get_string_fields(schema: pa.Schema) -> set[str]:
    """Extract field names that are string types from Arrow schema.

    Identifies fields that need JSON serialization for complex values.
    Handles both regular string and large_string Arrow types.

    Args:
        schema: PyArrow schema to inspect.

    Returns:
        Set of field names that are string types.

    Example:
        >>> schema = pa.schema([
        ...     pa.field("id", pa.int64()),
        ...     pa.field("name", pa.string()),
        ...     pa.field("data_json", pa.large_string()),
        ... ])
        >>> _get_string_fields(schema)
        {'name', 'data_json'}
    """
    return {
        field.name
        for field in schema
        if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
    }


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
    ) -> None:
        """Initialize base Delta writer.

        Args:
            base_path: Base path for Delta table storage.
                      Tables are stored as subdirectories (e.g., base_path/chembl/activity/).
            logger: Structured logger for observability (MUST be injected per RULES.md).
        """
        self.base_path = str(base_path).rstrip("/")
        self.logger = logger
        self._retention_manager = RetentionManager(base_path)

    def _prepare_arrow_data(
        self,
        records: list[dict[str, Any]],
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
        schema_fields = set(schema.names)
        string_fields = _get_string_fields(schema)

        filtered_records = [
            {
                k: _serialize_value(v, k in string_fields)
                for k, v in rec.items()
                if k in schema_fields
            }
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)
        return self._sort_by_primary_keys(arrow_data, primary_keys, schema.names)

    def _sort_by_primary_keys(
        self,
        table: pa.Table,
        primary_keys: list[str],
        schema_names: list[str],
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
        if not primary_keys:
            return table

        valid_keys = [pk for pk in primary_keys if pk in schema_names]
        if valid_keys:
            return table.sort_by([(pk, "ascending") for pk in valid_keys])

        self.logger.warning(
            "Primary keys not found in schema, skipping sort",
            primary_keys=primary_keys,
            schema_fields=schema_names,
        )
        return table

    async def _get_table_schema(self, table_name: str) -> pa.Schema | None:
        """Get existing table schema if table exists.

        Retrieves the PyArrow schema from an existing Delta table.
        Used for schema evolution checks and validation.

        Args:
            table_name: Table name in dot notation (e.g., 'chembl.activity').

        Returns:
            PyArrow Schema if table exists, None otherwise.
        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return dt.schema().to_arrow()
        except DeltaTableNotFoundError:
            return None

    def get_table_path(self, table_name: str) -> Path:
        """Get the filesystem path for a Delta table.

        Converts dot-notation table names to filesystem paths.

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

        return Path(self.base_path) / table_name.replace(".", "/")

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
        import shutil
        from pathlib import Path

        base = Path(self.base_path)
        if not base.exists():
            return 0

        cleared = 0
        if table_name:
            table_path = self.get_table_path(table_name)
            if table_path.exists():
                if not dry_run:
                    shutil.rmtree(table_path)
                cleared = 1
        else:
            for item in base.iterdir():
                if item.is_dir() and (item / "_delta_log").exists():
                    if not dry_run:
                        shutil.rmtree(item)
                    cleared += 1
        return cleared
