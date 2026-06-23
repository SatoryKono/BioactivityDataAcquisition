"""Clear and cleanup operations mixin for StorageBundle."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageBundleClearMixin"]


class StorageBundleClearMixin:
    """Mixin providing clear/cleanup operations for Silver, Gold, CSV, and Delta."""

    silver: SilverWriter
    gold: GoldWriter

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Implements SilverStoragePort.clear_silver().
        Clears both Delta tables and CSV exports (if configured).

        Args:
            table_name: Database table name.
            dry_run: Dry run mode flag.

        Returns:
            Computed integer value.
        """
        return await self._run_clear(self.silver, table_name, dry_run)

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Implements GoldStoragePort.clear_gold().
        Clears both Delta tables and CSV exports (if configured).

        Args:
            table_name: Database table name.
            dry_run: Dry run mode flag.

        Returns:
            Computed integer value.
        """
        return await self._run_clear(self.gold, table_name, dry_run)

    async def _run_clear(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
        dry_run: bool,
    ) -> int:
        """Execute clear operation for a writer."""
        loop = asyncio.get_running_loop()
        cleared = await loop.run_in_executor(
            None, lambda: writer.clear(table_name, dry_run=dry_run)
        )
        if writer.csv_exporter and not dry_run:
            exporter = writer.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared += len(deleted)
        return int(cleared)

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Implements StorageMaintenancePort.clear_csv().

        Args:
            table_name: Database table name.

        Returns:
            Computed integer value.
        """
        count = 0
        loop = asyncio.get_running_loop()

        if self.silver.csv_exporter:
            exporter = self.silver.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        if self.gold.csv_exporter:
            exporter = self.gold.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        return count

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Implements StorageMaintenancePort.clear_delta().

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Number of tables cleared.
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        if table_name:
            cleared_count += await loop.run_in_executor(
                None, lambda: self.silver.clear(table_name)
            )
            cleared_count += await loop.run_in_executor(
                None, lambda: self.gold.clear(table_name)
            )

        return cleared_count
