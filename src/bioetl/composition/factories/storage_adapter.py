"""StorageAdapter - Unified storage adapter for Bronze/Silver/Gold layers.

Implements StoragePort protocol from domain/ports.py.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from bioetl.domain.locking import LockContext
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType


__all__ = ["StorageAdapter"]


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from domain/ports.py.
    Delegates to specialized writers for each layer.
    """

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: DeltaWriter,
        gold_writer: GoldWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        lock_context: LockContext | None = None,
        **kwargs: Any,
    ) -> Path:
        """Write raw records to Bronze layer.

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name.
            entity: Entity type.
            date: Date for path partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
            lock_context: Lock context for validation (RULES.md §3.3).

        Returns:
            Path: Relative path to the written file.
        """
        return await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            lock_context=lock_context,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        lock_context: LockContext | None = None,
        **kwargs: Any,
    ) -> None:
        """Write transformed records to Silver layer."""
        await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            lock_context=lock_context,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: Any,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        lock_context: LockContext | None = None,
        **kwargs: Any,
    ) -> None:
        """Write aggregated records to Gold layer.

        Args:
            table_name: Target table name
            records: Records to write
            schema: Pandera schema for validation
            primary_keys: Optional primary key columns
            mode: Write mode
            ingestion_ts: Ingestion timestamp for audit (ADR-014)
            run_id: Run identifier for audit correlation
            lock_context: Lock context for validation (RULES.md §3.3).
        """
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            mode=mode,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            lock_context=lock_context,
        )

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Implements StoragePort.clear_silver().
        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        # Clear Silver Delta table (sync operation wrapped in executor)
        cleared_count += await loop.run_in_executor(
            None, lambda: self.silver.clear(table_name, dry_run=dry_run)
        )

        # Clear Silver CSV if exporter is configured
        if self.silver.csv_exporter and not dry_run:
            exporter = self.silver.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared_count += len(deleted)

        return cleared_count

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Implements StoragePort.clear_gold().
        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        # Clear Gold Delta table (sync operation wrapped in executor)
        cleared_count += await loop.run_in_executor(
            None, lambda: self.gold.clear(table_name, dry_run=dry_run)
        )

        # Clear Gold CSV if exporter is configured
        if self.gold.csv_exporter and not dry_run:
            exporter = self.gold.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared_count += len(deleted)

        return cleared_count

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Implements StoragePort.clear_csv().

        Args:
            table_name: If provided, only clear CSV for this table.
                       If None, clear all CSV files.

        Returns:
            Number of files cleared.
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        if self.silver.csv_exporter:
            exporter = self.silver.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared_count += len(deleted) if isinstance(deleted, list) else deleted

        if self.gold.csv_exporter:
            exporter = self.gold.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared_count += len(deleted) if isinstance(deleted, list) else deleted

        return cleared_count

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Implements StoragePort.clear_delta().

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

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> dict[str, Any]:
        """Preview what would be cleared without actual deletion.

        Implements StoragePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        result: dict[str, Any] = {
            "silver": self._preview_layer(self.silver, silver_table),
            "gold": None,
            "total_files": 0,
        }

        if gold_table:
            result["gold"] = self._preview_layer(self.gold, gold_table)

        result["total_files"] = result["silver"]["file_count"] + (
            result["gold"]["file_count"] if result["gold"] else 0
        )
        return result

    def _preview_layer(
        self,
        writer: DeltaWriter | GoldWriter,
        table_name: str,
    ) -> dict[str, Any]:
        """Count files in a layer without deletion.

        Args:
            writer: Delta or Gold writer instance
            table_name: Table name to preview

        Returns:
            Dict with path, file_count, and exists status.
        """
        path = writer.get_table_path(table_name)
        file_count = 0
        exists = path.exists()

        if exists:
            file_count = sum(1 for f in path.rglob("*") if f.is_file())

        return {
            "path": str(path),
            "file_count": file_count,
            "exists": exists,
        }

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        pass  # Writers don't need explicit cleanup

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and write capability.

        Validates Bronze, Silver, and Gold directories are writable by
        attempting to create and delete a temporary file in each layer.

        Returns:
            HealthStatus:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (1-2 layers have issues)
            - UNHEALTHY: Critical storage failure (all layers unavailable)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._check_storage_health_sync)

    def _check_storage_health_sync(self) -> HealthStatus:
        """Synchronous storage health check implementation.

        Checks if each layer's base directory is writable.
        """
        # Convert to Path objects since DeltaWriter and GoldWriter store as strings
        layers = [
            ("bronze", Path(self.bronze.base_path)),
            ("silver", Path(self.silver.base_path)),
            ("gold", Path(self.gold.base_path)),
        ]

        issues = 0
        for _layer_name, base_path in layers:
            if not self._check_directory_writable(base_path):
                issues += 1

        if issues == 0:
            return HealthStatus.HEALTHY
        elif issues < len(layers):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table via underlying writers.

        Implements StoragePort.vacuum().
        Vacuums both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name in format "provider.entity"
            retention_hours: Minimum age of files to remove (default 168h = 7 days)
            dry_run: If True, only report what would be removed

        Returns:
            Total number of files removed (or would be removed if dry_run)
        """
        total_removed = 0

        # Vacuum Silver
        try:
            removed = await self.silver.vacuum(
                table_name=table_name,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )
            total_removed += len(removed)
        except Exception:
            # Log but continue to Gold (table may not exist)
            pass

        # Vacuum Gold (GoldWriter uses DeltaWriter internally, need to add vacuum)
        # Gold layer uses same Delta format, so we can vacuum via path
        try:
            gold_table_path = f"{self.gold.base_path}/{table_name.replace('.', '/')}"
            loop = asyncio.get_running_loop()
            from deltalake import DeltaTable
            from deltalake.exceptions import (
                TableNotFoundError as DeltaTableNotFoundError,
            )

            try:
                dt = await loop.run_in_executor(
                    None,
                    lambda: DeltaTable(gold_table_path),
                )
                removed = await loop.run_in_executor(
                    None,
                    lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
                )
                total_removed += len(removed)
            except DeltaTableNotFoundError:
                pass
        except Exception:
            pass

        return total_removed

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive table to target path.

        Implements StoragePort.archive().
        Archives both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived
        """
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

    @staticmethod
    def _check_directory_writable(dir_path: Path | str) -> bool:
        """Check if a directory is writable.

        Args:
            dir_path: Directory path to check (accepts Path or str).

        Returns:
            True if directory is writable, False otherwise.
        """
        try:
            # Convert to Path if string
            path = Path(dir_path) if isinstance(dir_path, str) else dir_path

            # Ensure directory exists
            path.mkdir(parents=True, exist_ok=True)

            # Try to create and delete a temporary file
            temp_file = path / ".health_check_probe"
            temp_file.touch()
            temp_file.unlink()
            return True
        except (OSError, PermissionError):
            return False
