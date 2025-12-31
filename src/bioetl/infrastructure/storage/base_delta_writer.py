"""Base class for Delta Lake writers."""

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
    """Serialize a value for Arrow storage."""
    if value is None:
        return None
    if is_string_field and isinstance(value, (dict, list)):
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return value


def _get_string_fields(schema: pa.Schema) -> set[str]:
    """Extract field names that are string types."""
    return {
        field.name
        for field in schema
        if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
    }


class BaseDeltaWriter:
    """Base class with common functionality for Delta Lake writers."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
    ) -> None:
        self.base_path = str(base_path).rstrip("/")
        self.logger = logger
        self._retention_manager = RetentionManager(base_path)

    def _prepare_arrow_data(
        self,
        records: list[dict[str, Any]],
        schema: pa.Schema,
        primary_keys: list[str],
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting."""
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
        """Sort Arrow table by primary keys if valid."""
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
        """Get existing table schema if table exists."""
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
        """Get the filesystem path for a table."""
        from pathlib import Path

        return Path(self.base_path) / table_name.replace(".", "/")

    def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
        """Clear Delta table(s)."""
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
