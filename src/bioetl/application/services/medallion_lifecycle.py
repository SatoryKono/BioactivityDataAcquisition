"""Medallion lifecycle service (Application layer - orchestration).

Implements RULES.md §2.1-2.3 medallion architecture lifecycle operations.
This service manages clearing, vacuum, and future archive operations.

All medallion layer operations are consolidated here:
- prepare_for_run(): Pre-run clearing based on run type policy
- finalize_run(): Post-run vacuum operations
- clear(): Direct clearing based on policy
- vacuum(): Single table vacuum operation
- archive(): Cold storage archival
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.ports import LoggerPort, MetricsPort, StoragePort


@dataclass(frozen=True, slots=True)
class ClearResult:
    """Result of clear operation.

    Attributes:
        silver_cleared: Number of Silver records cleared.
        gold_cleared: Number of Gold records cleared.
        dry_run: Whether this was a dry run (no actual deletion).
    """

    silver_cleared: int
    gold_cleared: int
    dry_run: bool

    @property
    def total_cleared(self) -> int:
        """Get total records cleared.

        Returns:
            Sum of silver and gold cleared records.
        """
        return self.silver_cleared + self.gold_cleared


@dataclass(frozen=True, slots=True)
class VacuumResult:
    """Result of VACUUM operation.

    Attributes:
        silver_files_removed: Number of files removed from Silver table.
        gold_files_removed: Number of files removed from Gold table.
        skipped: Whether VACUUM was skipped.
    """

    silver_files_removed: int
    gold_files_removed: int
    skipped: bool


@dataclass(frozen=True, slots=True)
class PrepareResult:
    """Result of prepare_for_run operation.

    Combines clear result with policy used for transparency.

    Attributes:
        clear_result: Result of clear operation.
        policy: MedallionPolicy used for the operation.
    """

    clear_result: ClearResult
    policy: MedallionPolicy


@dataclass
class MedallionLifecycleService:
    """Unified service for managing medallion layer lifecycle operations.

    Consolidates all medallion lifecycle operations under one interface:
    - Pre-run: prepare_for_run() clears layers based on run type policy
    - Post-run: finalize_run() vacuums tables to reclaim storage
    - Direct: clear(), vacuum(), archive() for fine-grained control

    This service replaces the separate LifecycleOrchestrator and vacuum
    logic previously scattered across PostrunService.

    Attributes:
        storage: StoragePort for data layer operations.
        logger: Structured logger for observability.

    Example:
        >>> # Unified lifecycle for pipeline runs
        >>> service = MedallionLifecycleService(storage=storage, logger=logger)
        >>> # Pre-run: clear based on run type
        >>> prepare_result = await service.prepare_for_run(config, runtime)
        >>> # Post-run: vacuum if enabled
        >>> vacuum_result = await service.finalize_run(config, runtime)
    """

    storage: StoragePort
    logger: LoggerPort

    async def clear(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        dry_run: bool = False,
    ) -> ClearResult:
        """Clear medallion layers according to policy.

        Enforces medallion architecture invariants:
        - Only clears based on policy (not run type directly)
        - Logs all operations for observability

        Args:
            policy: Medallion policy determining what to clear.
            silver_table: Silver table name.
            gold_table: Gold table name.
            dry_run: If True, only count without deleting.

        Returns:
            ClearResult with counts of cleared records.
        """
        silver_cleared = 0
        gold_cleared = 0

        if policy.should_clear_silver:
            silver_cleared = await self.storage.clear_silver(
                silver_table, dry_run=dry_run
            )

        if policy.should_clear_gold:
            gold_cleared = await self.storage.clear_gold(gold_table, dry_run=dry_run)

        result = ClearResult(
            silver_cleared=silver_cleared,
            gold_cleared=gold_cleared,
            dry_run=dry_run,
        )

        self._log_result(policy, silver_table, gold_table, result)

        return result

    def _log_result(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        result: ClearResult,
    ) -> None:
        """Log clear operation result.

        Args:
            policy: The medallion policy used.
            silver_table: Silver table name.
            gold_table: Gold table name.
            result: The clear operation result.
        """
        if result.dry_run:
            self.logger.info(
                "DRY RUN: Would clear storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_would_clear": result.silver_cleared,
                    "gold_would_clear": result.gold_cleared,
                },
            )
        elif result.total_cleared > 0:
            self.logger.info(
                "Cleared storage",
                extra={
                    "policy": policy.clear_policy.value,
                    "silver_cleared": result.silver_cleared,
                    "gold_cleared": result.gold_cleared,
                },
            )

    async def vacuum(
        self,
        table: str,
        retention_days: int = 7,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table to reclaim storage space.

        Removes files older than retention period that are no longer
        referenced by the Delta log. Safe to run concurrently with reads.

        Args:
            table: Table name in format "provider.entity"
            retention_days: Minimum age of files to remove (default 7)
            dry_run: If True, only report what would be removed

        Returns:
            Number of files removed

        Raises:
            StorageError: If vacuum fails
        """
        retention_hours = retention_days * 24

        self.logger.info(
            "Starting vacuum operation",
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        try:
            files_removed = await self.storage.vacuum(
                table_name=table,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )

            self.logger.info(
                "Vacuum completed",
                table=table,
                files_removed=files_removed,
                dry_run=dry_run,
            )

            return files_removed

        except Exception as e:
            self.logger.error(
                "Vacuum failed",
                table=table,
                error=str(e),
            )
            raise

    async def archive(
        self,
        table: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive Delta table to cold storage.

        Copies table data to archive location. Optionally removes source
        after successful copy.

        Args:
            table: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived

        Raises:
            StorageError: If archive fails
        """
        self.logger.info(
            "Starting archive operation",
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        try:
            files_archived = await self.storage.archive(
                table_name=table,
                target_path=target_path,
                remove_source=remove_source,
            )

            self.logger.info(
                "Archive completed",
                table=table,
                files_archived=files_archived,
            )

            return files_archived

        except Exception as e:
            self.logger.error(
                "Archive failed",
                table=table,
                error=str(e),
            )
            raise

    # =========================================================================
    # High-level pipeline lifecycle operations
    # =========================================================================

    async def prepare_for_run(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
    ) -> PrepareResult:
        """Prepare medallion layers for pipeline run.

        Clears Silver/Gold tables based on run type policy:
        - REBUILD/BACKFILL: Clear both Silver and Gold
        - INCREMENTAL: Never clear (merge/upsert behavior)

        This method consolidates logic previously in LifecycleOrchestrator.

        Args:
            config: Pipeline configuration with table names.
            runtime: Runtime configuration with run type and dry_run flag.

        Returns:
            PrepareResult with clear result and policy used.
        """
        from bioetl.domain.medallion import MedallionPolicy

        policy = MedallionPolicy.for_run_type(runtime.run_type)

        gold_table = config.gold_table or f"{config.provider}.{config.entity_type}"

        result = await self.clear(
            policy=policy,
            silver_table=config.silver_table,
            gold_table=gold_table,
            dry_run=runtime.dry_run,
        )

        self.logger.debug(
            "Medallion prepare completed",
            extra={
                "run_type": runtime.run_type.value,
                "clear_policy": policy.clear_policy.value,
                "silver_cleared": result.silver_cleared,
                "gold_cleared": result.gold_cleared,
            },
        )

        return PrepareResult(clear_result=result, policy=policy)

    async def finalize_run(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        metrics: MetricsPort | None = None,
    ) -> VacuumResult:
        """Finalize medallion layers after pipeline run.

        Vacuums Silver and Gold tables if enabled:
        - Skipped if runtime.vacuum_after_run is False
        - Skipped in dry-run mode

        This method consolidates vacuum logic previously scattered in PostrunService.

        Args:
            config: Pipeline configuration with table names.
            runtime: Runtime configuration with vacuum settings.
            metrics: Optional metrics port for observability.

        Returns:
            VacuumResult with files removed counts.
        """
        if not runtime.vacuum_after_run:
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        if runtime.dry_run:
            self.logger.info(
                "VACUUM skipped in dry-run mode",
                extra={"stage": "vacuum"},
            )
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        self.logger.info(
            "Starting VACUUM operation",
            extra={
                "stage": "vacuum",
                "retention_days": runtime.vacuum_retention_days,
            },
        )

        gold_table = config.gold_table or f"{config.provider}.{config.entity_type}"

        silver_files = await self._vacuum_table_safe(
            table=config.silver_table,
            layer="silver",
            retention_days=runtime.vacuum_retention_days,
            metrics=metrics,
            pipeline_name=config.pipeline_name,
        )
        gold_files = await self._vacuum_table_safe(
            table=gold_table,
            layer="gold",
            retention_days=runtime.vacuum_retention_days,
            metrics=metrics,
            pipeline_name=config.pipeline_name,
        )

        return VacuumResult(
            silver_files_removed=silver_files,
            gold_files_removed=gold_files,
            skipped=False,
        )

    async def _vacuum_table_safe(
        self,
        table: str,
        layer: str,
        retention_days: int,
        metrics: MetricsPort | None,
        pipeline_name: str,
    ) -> int:
        """Vacuum a single table with error handling.

        Gracefully handles errors to avoid failing the entire pipeline
        due to vacuum issues.

        Args:
            table: Table name to vacuum.
            layer: Layer name for metrics (silver/gold).
            retention_days: Retention period in days.
            metrics: Optional metrics port.
            pipeline_name: Pipeline name for metrics tags.

        Returns:
            Number of files removed (0 on error).
        """
        try:
            files_removed = await self.vacuum(
                table=table,
                retention_days=retention_days,
                dry_run=False,
            )
            self.logger.info(
                f"VACUUM completed for {layer.capitalize()} table",
                extra={
                    "table": table,
                    "files_removed": files_removed,
                },
            )

            if metrics:
                metrics.increment_counter(
                    "vacuum_files_removed",
                    files_removed,
                    {"pipeline": pipeline_name, "layer": layer},
                )
            return files_removed
        except Exception as e:
            self.logger.warning(
                f"VACUUM failed for {layer.capitalize()} table",
                extra={"table": table, "error": str(e)},
            )
            return 0


__all__ = [
    "ClearResult",
    "MedallionLifecycleService",
    "PrepareResult",
    "VacuumResult",
]
