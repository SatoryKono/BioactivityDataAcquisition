"""Maintenance and export helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMaintenanceMixin"]

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import pyarrow as pa

from bioetl.domain.medallion import SilverWriteMode

if TYPE_CHECKING:
    from datetime import datetime

    from deltalake import DeltaTable

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BronzeRecord, MetaDict
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.storage.retention_manager import RetentionManager


class SilverWriterMaintenanceMixin:
    """Mixin with CSV export, vacuum, optimize, and table read helpers."""

    logger: LoggerPort
    csv_exporter: CsvExporter | None
    _retention_manager: RetentionManager
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
        """Export data to CSV if exporter is configured."""
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

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Remove old files not referenced by the Delta log."""
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
        """Optimize table layout (compaction)."""
        return await self._retention_manager.optimize(
            table_name,
            target_size=target_size,
            partition_filters=partition_filters,
        )

    async def get_table_info(self, table_name: str) -> MetaDict:
        """Get metadata about a Delta table."""
        return await self._retention_manager.get_table_info(table_name)

    async def time_travel(
        self,
        table_name: str,
        version: int | None = None,
        timestamp: datetime | None = None,
    ) -> DeltaTable:
        """Read a previous version of a table."""
        return await self._retention_manager.time_travel(
            table_name,
            version=version,
            timestamp=timestamp,
        )

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Read records from a Silver layer Delta table."""
        return await self.read_table(table_name, columns=columns)
