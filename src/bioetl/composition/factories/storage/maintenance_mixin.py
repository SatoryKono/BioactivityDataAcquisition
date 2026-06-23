"""Maintenance operations mixin for StorageBundle (vacuum, optimize, archive)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bioetl.application.runtime_clock import current_utc_time

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageBundleMaintenanceMixin"]


def _is_delta_table_dir(path: Path) -> bool:
    """Return True when a directory contains a Delta log with at least one commit file."""
    delta_log = path / "_delta_log"
    if not delta_log.is_dir():
        return False
    return any(delta_log.iterdir())


class StorageBundleMaintenanceMixin:
    """Mixin providing maintenance operations: optimize, vacuum, archive, cleanup."""

    bronze: BronzeWriter
    silver: SilverWriter
    gold: GoldWriter

    def is_table_initialized(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> bool:
        """Check whether a Delta table has been written to."""
        writer = self.gold if layer == "gold" else self.silver
        table_path = writer.get_table_path(table_name)
        return _is_delta_table_dir(table_path)

    def get_table_version(
        self,
        table_path: str,
        *,
        layer: Literal["silver", "gold"] = "silver",
    ) -> int | None:
        """Return the current Delta table version, or None if table does not exist."""
        del layer
        path = Path(table_path)
        if not _is_delta_table_dir(path):
            return None
        try:
            from deltalake import DeltaTable

            return int(DeltaTable(table_path).version())
        except (OSError, RuntimeError, ValueError, ImportError):
            return None

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity.

        Performs Delta-table maintenance only. Bronze retention is an explicit
        maintenance operation and must not run implicitly during postrun
        compaction/vacuum flows for the active pipeline run.

        Args:
            table_name: Target identifier (e.g., 'provider.entity' for Delta/Bronze)
            retention_hours: Retention period in hours (default 168h = 7 days)
            dry_run: If True, only log what would be done without action
        """
        await self.vacuum(table_name, retention_hours, dry_run)
        if "." not in table_name:
            return
        provider, entity = table_name.split(".", 1)
        cutoff_date = current_utc_time() - timedelta(hours=retention_hours)
        await self.bronze.cleanup_old_files(
            cutoff_date=cutoff_date,
            dry_run=dry_run,
            provider=provider,
            entity=entity,
        )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table via underlying writers.

        Implements StorageMaintenancePort.vacuum().
        Vacuums both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name in format "provider.entity"
            retention_hours: Minimum age of files to remove (default 168h = 7 days)
            dry_run: If True, only report what would be removed

        Returns:
            Total number of files removed (or would be removed if dry_run)
        """
        total_removed = 0

        # Vacuum Silver (only if table exists)
        silver_table_path = self.silver.get_table_path(table_name)
        if _is_delta_table_dir(silver_table_path):
            removed = await self.silver.vacuum(
                table_name=table_name,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )
            total_removed += len(removed)

        # Vacuum Gold only when the directory is a real Delta table.
        # Metadata-only directories can exist when Gold writes are disabled.
        gold_table_path = self.gold.get_table_path(table_name)
        if _is_delta_table_dir(gold_table_path):
            from deltalake import DeltaTable

            loop = asyncio.get_running_loop()
            try:
                dt = await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(str(gold_table_path)),
                )
                removed = await loop.run_in_executor(
                    None,
                    lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
                )
                total_removed += len(removed)
            except (OSError, RuntimeError):
                pass

        return total_removed

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Silver and Gold table directories to a target path."""
        import shutil

        total_archived = 0

        # Archive Silver
        silver_table_path = self.silver.get_table_path(table_name)
        if silver_table_path.exists():
            silver_target = Path(target_path) / "silver" / table_name.replace(".", "/")
            silver_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(silver_table_path, silver_target),
            )
            total_archived += sum(
                1 for f in silver_table_path.rglob("*") if f.is_file()
            )
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(silver_table_path),
                )

        # Archive Gold
        gold_table_path = self.gold.get_table_path(table_name)
        if gold_table_path.exists():
            gold_target = Path(target_path) / "gold" / table_name.replace(".", "/")
            gold_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(gold_table_path, gold_target),
            )
            total_archived += sum(1 for f in gold_table_path.rglob("*") if f.is_file())
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(gold_table_path),
                )

        return total_archived

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int:
        """Deduplicate Silver table by primary keys after append-mode writes.

        Args:
            table_name: Logical Silver table name.
            primary_keys: Business key columns for deduplication.

        Returns:
            Number of duplicate rows removed.
        """
        return int(await self.silver.deduplicate_silver(table_name, primary_keys))

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention).

        Implements BronzeStoragePort.cleanup_bronze().
        Delegates to BronzeWriter.cleanup_old_files().

        Args:
            cutoff_date: Files older than this date will be removed.
            dry_run: If True, only count what would be removed.

        Returns:
            Dictionary with cleanup statistics.
        """
        return dict(
            await self.bronze.cleanup_old_files(
                cutoff_date=cutoff_date,
                dry_run=dry_run,
            )
        )
