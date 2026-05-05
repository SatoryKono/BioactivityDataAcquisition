"""Maintenance and export helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMaintenanceMixin"]

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
from deltalake import DeltaTable

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import BronzeRecord, MetaDict
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterPort
from bioetl.infrastructure.storage.support.retention import RetentionPolicy


class SilverWriterMaintenanceMixin:
    """Mixin with CSV export, vacuum, optimize, and table read helpers."""

    logger: LoggerPort
    csv_exporter: CsvExporterPort | None
    _retention_manager: RetentionPolicy
    get_table_path: Callable[[str], Path]
    read_table: Callable[..., Awaitable[list[BronzeRecord]]]

    async def _maybe_export_csv(
        self,
        *,
        table_name: str,
        arrow_data: pa.Table,
        mode: str,
        validated_mode: SilverWriteMode,
        primary_keys: list[str],
    ) -> None:
        """Export data to CSV if exporter is configured.

        Args:
            table_name: Logical table name for the export target.
            arrow_data: PyArrow table containing the records to export.
            mode: Write mode string (e.g., "delete", "merge", "append").
            validated_mode: Silver write mode enum for determining CSV append behavior.
            primary_keys: List of primary key columns for deduplication in merge exports.
        """
        if not self.csv_exporter:
            return
        csv_append = mode != "delete"
        csv_primary_keys = (
            primary_keys if validated_mode == SilverWriteMode.MERGE else None
        )
        await self.csv_exporter.export(
            table_name,
            arrow_data,
            append=csv_append,
            primary_keys=csv_primary_keys,
        )

    async def finalize_csv_export(
        self,
        table_name: str,
        primary_keys: list[str] | None = None,
    ) -> None:
        """One-shot CSV finalize: deduplicate and sort after all batches.

        Args:
            table_name: Logical table name whose CSV export to finalize.
            primary_keys: Optional primary key columns for deduplication.
        """
        if self.csv_exporter:
            await self.csv_exporter.finalize_csv(
                table_name,
                primary_keys=primary_keys,
            )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files not referenced by the Delta log.

        Args:
            table_name: Logical table name to vacuum.
            retention_hours: Optional retention period in hours; defaults to Delta table setting.
            dry_run: If True, list files without removing them.

        Returns:
            List of file path strings that were removed (or would be removed in dry_run mode).
        """
        return await self._retention_manager.vacuum(
            table_name,
            retention_hours=retention_hours,
            dry_run=dry_run,
        )

    async def optimize(
        self,
        table_name: str,
        target_size: int | None = None,
        partition_filters: (
            list[
                tuple[str, str, Any]  # Any: Delta Lake partition filter values vary
            ]  # Any: Delta Lake partition filter values vary
            | None
        ) = None,  # Any: Delta Lake partition filter values vary
    ) -> MetaDict:
        """Optimize table layout (compaction).

        Args:
            table_name: Logical table name to optimize.
            target_size: Optional target file size in bytes for compaction.
            partition_filters: Optional list of partition filter tuples to restrict compaction scope.

        Returns:
            Dictionary with compaction metrics and file statistics.
        """
        return await self._retention_manager.optimize(
            table_name,
            target_size=target_size,
            partition_filters=partition_filters,
        )

    async def get_table_info(self, table_name: str) -> MetaDict:
        """Get metadata about a Delta table.

        Args:
            table_name: Logical table name to retrieve metadata for.

        Returns:
            Dictionary with table metadata including version, schema, and file counts.
        """
        return await self._retention_manager.get_table_info(table_name)

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read a previous version of a table.

        Args:
            table_name: Logical table name to time-travel on.
            version: Optional Delta table version number to load.
            timestamp: Optional point-in-time timestamp to load the table at.

        Returns:
            DeltaTable instance loaded at the specified version or timestamp.
        """
        return await self._retention_manager.time_travel(
            table_name,
            version=version,
            timestamp=timestamp,
        )

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        """Deduplicate Silver table by primary keys after append-mode writes.

        Args:
            table_name: Logical table name to deduplicate.
            primary_keys: Business key columns for deduplication.

        Returns:
            Number of duplicate rows removed.
        """
        return await self._retention_manager.deduplicate_silver(
            table_name,
            primary_keys=primary_keys,
        )

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Read records from a Silver layer Delta table.

        Args:
            table_name: Logical table name to read from.
            columns: Optional list of column names to select; reads all columns if None.

        Returns:
            List of record dictionaries from the Silver Delta table.
        """
        return await self.read_table(table_name, columns=columns)

    def preview_cleanup(
        self,
        table_name: str,
    ) -> MetaDict:  # Any: preview payload has heterogeneous values
        """Preview Silver cleanup scope without deleting files.

        Args:
            table_name: Logical table name to inspect.

        Returns:
            Dictionary with path, existence flag, and file count for the Silver table directory.
        """
        table_path = self.get_table_path(table_name)
        exists = table_path.exists()
        file_count = (
            sum(1 for file_path in table_path.rglob("*") if file_path.is_file())
            if exists
            else 0
        )
        return {
            "path": str(table_path),
            "file_count": file_count,
            "exists": exists,
        }
