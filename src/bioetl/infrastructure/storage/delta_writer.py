"""Silver layer writer (Delta Lake with merge/upsert).

Implements RULES.md §2.1.1 - Silver Layer specifications.

Requirements:
- REQ-DATA-006: Delta Lake format (ACID transactions)
- REQ-DATA-007: Merge/Upsert strategy
- REQ-DATA-008: Time Travel support
- REQ-DELTA-001: Protocol Version (Writer 2, Reader 1)
- REQ-DELTA-002: VACUUM scheduler (7-day retention)
- REQ-DELTA-003: Forensic retention (7-30 days configurable)
- REQ-LINEAGE-001: Records contain _source_batch_id

Architecture:
- Uses deltalake (delta-rs) for Python
- Local filesystem storage
- Supports partitioning for query optimization
- Implements merge/upsert based on primary keys
- ACID guarantees for concurrent writes
- CSV export delegated to CsvExporter (composition)
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import DeltaError, SchemaMismatchError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import (
    MergeConflictError,
    SchemaViolationError,
    TableNotFoundError,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


class DeltaWriter:
    """Writer for Silver layer (normalized data in Delta Lake).

    Implements merge/upsert strategy to handle updates and deduplication.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

    def __init__(
        self,
        base_path: str | Path,
        csv_exporter: CsvExporter | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize Delta writer.

        Args:
            base_path: Base path for Delta tables (local filesystem)
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
            logger: Optional logger for debug output

        """
        self.base_path = str(base_path).rstrip("/")
        self.csv_exporter = csv_exporter
        self.logger = logger

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
                return json.dumps(value, sort_keys=True)
            return value

        filtered_records = [
            {k: serialize_value(k, v) for k, v in rec.items() if k in schema_fields}
            for rec in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)

        if primary_keys:
            arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])
        return arrow_data

    async def _write_overwrite(
        self, table_path: str, data: pa.Table, partition_cols: list[str] | None
    ) -> None:
        """Write data in overwrite mode."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="overwrite",
                partition_by=partition_cols,
                schema_mode="overwrite",
            ),
        )

    async def _write_append(
        self, table_path: str, data: pa.Table, partition_cols: list[str] | None
    ) -> None:
        """Write data in append mode."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: write_deltalake(
                table_or_uri=table_path,
                data=data,
                mode="append",
                partition_by=partition_cols,
            ),
        )

    async def _write_merge(
        self,
        table_path: str,
        data: pa.Table,
        primary_keys: list[str],
        partition_cols: list[str] | None,
    ) -> None:
        """Write data using merge/upsert strategy."""
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            await self._merge_records(dt, data, primary_keys)
        except DeltaTableNotFoundError:
            await self._write_append(table_path, data, partition_cols)

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
    ) -> None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert)."""
        if not records:
            raise ValueError("No records to write")

        required_fields = {"_run_id", "_run_type", "_source_batch_id", "_ingestion_ts"}
        if missing_fields := required_fields - set(records[0].keys()):
            raise ValueError(
                f"Records missing required metadata fields: {missing_fields}"
            )

        if self.logger:
            # Debug logging for optional fields/record structure
            keys = set(records[0].keys())
            optional_missing = [k for k in schema.names if k not in keys]
            if optional_missing:
                self.logger.debug(
                    "Optional fields missing in batch",
                    table=table_name,
                    missing=optional_missing,
                )

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        arrow_data = self._prepare_arrow_data(records, schema, primary_keys)

        try:
            if mode == "overwrite":
                await self._write_overwrite(table_path, arrow_data, partition_cols)
            elif mode == "append":
                await self._write_append(table_path, arrow_data, partition_cols)
            else:
                await self._write_merge(
                    table_path, arrow_data, primary_keys, partition_cols
                )
        except (SchemaMismatchError, ArrowTypeError) as e:
            raise SchemaViolationError(table_name, errors=[str(e)]) from e
        except DeltaError as e:
            if "Merge-conflict" in str(e):
                raise MergeConflictError(table_name, conflicts=1) from e
            raise

        if self.csv_exporter:
            csv_append = mode != "overwrite"
            await self.csv_exporter.export(table_name, arrow_data, append=csv_append)

    async def _merge_records(
        self,
        dt: DeltaTable,
        records: pa.Table | pa.RecordBatchReader,
        primary_keys: list[str],
    ) -> None:
        """Merge records into existing Delta table."""
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in primary_keys
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: (
                dt.merge(
                    source=records,
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update_all(
                    predicate=(
                        "CASE "
                        "WHEN source._run_type = 'rebuild' THEN 3 "
                        "WHEN source._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END >= "
                        "CASE "
                        "WHEN target._run_type = 'rebuild' THEN 3 "
                        "WHEN target._run_type = 'backfill' THEN 2 "
                        "ELSE 1 END"
                    )
                )
                .when_not_matched_insert_all()
                .execute()
            ),
        )

    def get_table_path(self, table_name: str) -> Path:
        """Get the filesystem path for a table.

        Args:
            table_name: Table name (e.g., 'chembl.activity')

        Returns:
            Path to the table directory.

        """
        from pathlib import Path

        return Path(self.base_path) / table_name.replace(".", "/")

    def clear(self, table_name: str | None = None, dry_run: bool = False) -> int:
        """Clear Delta table(s) at the start of a pipeline run.

        Args:
            table_name: If provided, only clear this table.
                       If None, clear all tables in base_path.
            dry_run: If True, only count what would be deleted.

        Returns:
            Number of tables cleared (or would be cleared).

        """
        import shutil
        from pathlib import Path

        base = Path(self.base_path)
        if not base.exists():
            return 0

        cleared = 0
        if table_name:
            # Clear specific table
            table_path = self.get_table_path(table_name)
            if table_path.exists():
                if not dry_run:
                    shutil.rmtree(table_path)
                cleared = 1
        else:
            # Clear all Delta tables (directories with _delta_log)
            for item in base.iterdir():
                if item.is_dir() and (item / "_delta_log").exists():
                    if not dry_run:
                        shutil.rmtree(item)
                    cleared += 1

        return cleared

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files that are no longer referenced by the Delta log.

        Args:
            table_name: Table name.
            retention_hours: Hours of retention.
            dry_run: If True, only list files to be deleted.

        Returns:
            List of files deleted (or to be deleted).

        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return await loop.run_in_executor(
                None,
                lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
            )
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: list[tuple[str, str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Optimize table layout (compaction).

        Args:
            table_name: Table name.
            target_size: Target file size in bytes (currently unused, reserved for future).
            partition_filters: Optional filters to limit optimization to specific partitions.

        Returns:
            Optimization metrics.

        """
        # Note: target_size reserved for future delta-rs API support
        _ = target_size  # Suppress unused variable warning
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        filters = partition_filters  # Capture for lambda closure
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return await loop.run_in_executor(
                None, lambda: dt.optimize.compact(partition_filters=filters)
            )
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get metadata about a Delta table.

        Args:
            table_name: Table name.

        Returns:
            Dictionary with table metadata (version, files, history).

        """
        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()
        try:
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(table_path),
            )
            return {
                "version": dt.version(),
                "num_files": len(dt.files()),
                "schema": dt.schema().to_pyarrow(),
                "metadata": dt.metadata(),
            }
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read a previous version of the table.

        Args:
            table_name: Table name.
            version: Version number.
            timestamp: Timestamp string.

        Returns:
            PyArrow table or equivalent of the snapshot.

        """
        if version is not None and timestamp is not None:
            raise ValueError("Specify either version or timestamp, not both")

        table_path = f"{self.base_path}/{table_name.replace('.', '/')}"
        loop = asyncio.get_running_loop()

        try:
            if version is not None:
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        version=version,
                    ),
                )
            elif timestamp is not None:
                timestamp_str = timestamp.isoformat()
                return await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(
                        table_path,
                        storage_options={
                            "time_travel": timestamp_str,
                        },
                    ),
                )
            else:
                raise ValueError("Must specify either version or timestamp")
        except DeltaTableNotFoundError as e:
            raise TableNotFoundError(table_path) from e
