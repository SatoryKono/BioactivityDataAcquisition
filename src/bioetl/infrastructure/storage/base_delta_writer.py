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
        string_fields = {
            field.name
            for field in schema
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
        }

        def serialize_value(key: str, value: Any) -> Any:
            if value is None:
                return None
            if key in string_fields and isinstance(value, (dict, list)):
                return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
            return value

        filtered_records = [
            {k: serialize_value(k, v) for k, v in rec.items() if k in schema_fields}
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)

        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in schema.names]
            if valid_keys:
                arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in valid_keys])
            elif primary_keys:
                self.logger.warning(
                    "Primary keys not found in schema, skipping sort",
                    primary_keys=primary_keys,
                    schema_fields=schema.names,
                )
        return arrow_data

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
