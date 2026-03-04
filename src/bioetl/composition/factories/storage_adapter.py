"""StorageAdapter - Unified storage adapter for Bronze/Silver/Gold layers.

Implements StoragePort protocol from domain/ports.py.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.

Note:
    Lock validation is performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from bioetl.domain.contracts.gold.composite import (
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
)
from bioetl.domain.types import HealthStatus
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pandera.api.dataframe.container import DataFrameSchema

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType


__all__ = ["StorageAdapter"]


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from domain/ports.py.
    Delegates to specialized writers for each layer.
    """

    _COMPOSITE_GOLD_SCHEMAS: ClassVar[
        dict[str, Any]  # Any: record/metadata values are heterogeneous
    ] = {  # Any: factory wiring; concrete types resolved at runtime
        "composite/publication": CompositePublicationGoldSchema,
        "composite_publication": CompositePublicationGoldSchema,
        "composite/molecule": CompositeMoleculeGoldSchema,
        "composite_molecule": CompositeMoleculeGoldSchema,
    }

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: SilverWriter,
        gold_writer: GoldWriter,
    ):
        """Initialize StorageAdapter with injected layer writers.

        Args:
            bronze_writer: Writer for raw data ingestion into Bronze layer
                (zst-compressed JSONL files with optional JSON and metadata).
            silver_writer: Writer for transformed data into Silver layer
                (Delta Lake tables with schema enforcement and optional CSV export).
            gold_writer: Writer for aggregated/validated data into Gold layer
                (Delta Lake tables with Pandera validation and optional CSV export).
        """
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
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
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
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If None, a minimal
                           SourceMetadata is created with type="api".

        Returns:
            BronzeWriteResult: Result containing path, record count, sizes,
                and checksum for downstream lineage tracking.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
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
            source_metadata=source_metadata,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[
            dict[str, Any]  # Any: record/metadata values are heterogeneous
        ],  # Any: factory wiring; concrete types resolved at runtime
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift.
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            bronze_refs=bronze_refs,
            key_nullability_rules=key_nullability_rules,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[
            dict[str, Any]  # Any: record/metadata values are heterogeneous
        ],  # Any: factory wiring; concrete types resolved at runtime
        schema: Any,  # Any: Pandera DataFrameModel class varies per entity Gold schema
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: dict[str, Any]  # Any: record/metadata values are heterogeneous
        | None = None,  # Any: factory wiring; concrete types resolved at runtime
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[Any]  # Any: Delta Lake reference types vary
        | None = None,  # Any: factory wiring; concrete types resolved at runtime
    ) -> None:
        """Write aggregated records to Gold layer.

        Args:
            table_name: Target table name
            records: Records to write
            schema: Pandera schema for validation
            primary_keys: Optional primary key columns
            mode: Write mode
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp for audit (ADR-014)
            run_id: Run identifier for audit correlation
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            mode=mode,
            scd_config=scd_config,
            column_order=column_order,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            silver_refs=silver_refs,
        )

    def get_table_path(self, table_name: str) -> Path:
        """Resolve the full path to a Delta table.

        Delegates to the underlying writer implementation.

        Args:
            table_name: Database table name.

        Returns:
            Table path.
        """
        return self.silver.get_table_path(table_name)

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        dict[str, Any]  # Any: record/metadata values are heterogeneous
    ]:  # Any: factory wiring; concrete types resolved at runtime
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        return await self.silver.read_silver(table_name, columns=columns)

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[
            dict[str, Any]  # Any: record/metadata values are heterogeneous
        ],  # Any: factory wiring; concrete types resolved at runtime
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
        """
        await self.silver.write_silver_merged(
            table_name,
            records,
            primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[
            dict[str, Any]  # Any: record/metadata values are heterogeneous
        ],  # Any: factory wiring; concrete types resolved at runtime
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: DataFrameSchema | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
            schema: Optional Pandera schema for strict contract validation.
        """
        schema = self._COMPOSITE_GOLD_SCHEMAS.get(table_name)

        await self.gold.write_gold_merged(
            table_name,
            records,
            primary_keys,
            schema=schema,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Implements StoragePort.clear_silver().
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

        Implements StoragePort.clear_gold().
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
        return cleared

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Implements StoragePort.clear_csv().

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
    ) -> dict[str, Any]:  # Any: factory wiring; concrete types resolved at runtime
        """Preview what would be cleared without actual deletion.

        Implements StoragePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        result: dict[
            str, Any  # Any: record/metadata values are heterogeneous
        ] = {  # Any: factory wiring; concrete types resolved at runtime
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
        writer: SilverWriter | GoldWriter,
        table_name: str,
    ) -> dict[str, Any]:  # Any: factory wiring; concrete types resolved at runtime
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
        # Convert to Path objects since SilverWriter and GoldWriter store as strings
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

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity.

        Performs maintenance operations appropriate for the storage layer:
        - Delta Lake: Runs VACUUM to remove old files
        - JSONL/File: Removes files older than retention period

        Args:
            table_name: Target identifier (e.g., 'provider.entity' for Delta/Bronze)
            retention_hours: Retention period in hours (default 168h = 7 days)
            dry_run: If True, only log what would be done without action
        """
        # 1. Optimize Silver/Gold Delta Tables
        await self.vacuum(table_name, retention_hours, dry_run)

        # 2. Optimize Bronze (File cleanup)
        # Parse table_name to get provider/entity for targeted cleanup
        if "." in table_name:
            provider, entity = table_name.split(".", 1)
            cutoff_date = datetime.now(UTC) - timedelta(hours=retention_hours)
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

        # Vacuum Silver (only if table exists)
        silver_table_path = self.silver.get_table_path(table_name)
        if silver_table_path.exists():
            removed = await self.silver.vacuum(
                table_name=table_name,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )
            total_removed += len(removed)

        # Vacuum Gold (only if table exists)
        gold_table_path = self.gold.get_table_path(table_name)
        if gold_table_path.exists():
            from deltalake import DeltaTable

            loop = asyncio.get_running_loop()
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(str(gold_table_path)),
            )
            removed = await loop.run_in_executor(
                None,
                lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
            )
            total_removed += len(removed)

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

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention).

        Implements StoragePort.cleanup_bronze().
        Delegates to BronzeWriter.cleanup_old_files().

        Args:
            cutoff_date: Files older than this date will be removed.
            dry_run: If True, only count what would be removed.

        Returns:
            Dictionary with cleanup statistics.
        """
        return await self.bronze.cleanup_old_files(
            cutoff_date=cutoff_date,
            dry_run=dry_run,
        )

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
