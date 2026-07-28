# pyright: reportIncompatibleVariableOverride=false
# Host attrs/methods provided by concrete composition.
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
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.application.services.medallion.medallion_maintenance_mixin import (
    _MedallionMaintenanceMixin,
)
from bioetl.application.services.medallion.medallion_types import (
    ClearResult,
    PrepareResult,
    VacuumResult,
)
from bioetl.domain.exceptions import BioETLError, StorageError
from bioetl.domain.ports import StorageMaintenancePort

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
    )


class MedallionStorageProtocol(StorageMaintenancePort, Protocol):
    """Lifecycle-focused storage contract for medallion service."""

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear or count Silver records for one table."""
        ...

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear or count Gold records for one table."""
        ...


# Programming errors (ValueError/TypeError) must propagate, not look like storage
# failures (ARCH-CR-04 / #6866).
_LIFECYCLE_OPERATION_ERRORS = (
    StorageError,
    BioETLError,
    OSError,
    RuntimeError,
)


class _MedallionClearMixin:
    """Policy-driven clear operations for Silver/Gold layers.

    Enforces medallion architecture invariants by delegating clear decisions
    to a MedallionPolicy rather than accepting run type directly. All clearing
    is logged for observability and supports a dry-run mode.
    """

    storage: MedallionStorageProtocol = cast(Any, None)  # Any: host default (PD4)
    logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)

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

        self._log_clear_result(policy, silver_table, gold_table, result)

        return result

    def _log_clear_result(
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
                policy=policy.clear_policy.value,
                silver_table=silver_table,
                gold_table=gold_table,
                silver_would_clear=result.silver_cleared,
                gold_would_clear=result.gold_cleared,
            )
        elif result.total_cleared > 0:
            self.logger.info(
                "Cleared storage",
                policy=policy.clear_policy.value,
                silver_cleared=result.silver_cleared,
                gold_cleared=result.gold_cleared,
            )


class _MedallionRunLifecycleMixin(_MedallionClearMixin):
    """High-level run orchestration for pre/post lifecycle operations.

    Extends _MedallionClearMixin with pipeline-level prepare and finalize
    hooks. prepare_for_run() derives the correct MedallionPolicy from run
    type and clears layers accordingly. finalize_run() triggers storage
    optimization (vacuum/compact) when configured.
    """

    storage: MedallionStorageProtocol = cast(Any, None)  # Any: host default (PD4)
    logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)

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

        gold_table = config.effective_gold_table
        silver_table = config.effective_silver_table

        result = await self.clear(
            policy=policy,
            silver_table=silver_table,
            gold_table=gold_table,
            dry_run=runtime.dry_run,
        )

        self.logger.debug(
            "Medallion prepare completed",
            run_type=runtime.run_type.value,
            clear_policy=policy.clear_policy.value,
            silver_cleared=result.silver_cleared,
            gold_cleared=result.gold_cleared,
        )

        return PrepareResult(clear_result=result, policy=policy)

    async def finalize_run(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        metrics: MetricsPort | None = None,
    ) -> VacuumResult:
        """Finalize medallion layers after pipeline run.

        Optimizes storage (Vacuum/Cleanup) if enabled:
        - Skipped if neither optimize_storage nor vacuum_after_run is True
        - Uses StorageMaintenancePort.optimize() for unified maintenance

        Args:
            config: Pipeline configuration with table names.
            runtime: Runtime configuration with vacuum settings.
            metrics: Optional metrics port for observability.

        Returns:
            VacuumResult with actual Silver/Gold vacuum removal counts when run.
        """
        if not self._is_optimization_enabled(runtime):
            return VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )

        silver_table = config.effective_silver_table
        gold_table = config.effective_gold_table
        retention_hours = self._retention_hours(runtime.vacuum_retention_days)

        self.logger.info(
            "Starting storage optimization",
            stage="optimize",
            retention_days=runtime.vacuum_retention_days,
            dry_run=runtime.dry_run,
            target=silver_table,
        )

        try:
            silver_removed, gold_removed = await self._optimize_tables(
                silver_table=silver_table,
                gold_table=gold_table,
                retention_hours=retention_hours,
                dry_run=runtime.dry_run,
            )
            self._emit_optimization_metric(
                metrics=metrics,
                pipeline_name=config.pipeline_name,
                status="success",
            )
            return VacuumResult(
                silver_files_removed=silver_removed,
                gold_files_removed=gold_removed,
                skipped=False,
            )

        except _LIFECYCLE_OPERATION_ERRORS as e:
            self.logger.error(
                "storage_optimization_failed",
                pipeline=config.pipeline_name,
                error=str(e),
            )
            self._emit_optimization_metric(
                metrics=metrics,
                pipeline_name=config.pipeline_name,
                status="failed",
            )
            # Do not return a success-shaped vacuum result after failure (ARCH-CR-04).
            raise

    @staticmethod
    def _is_optimization_enabled(runtime: RuntimeConfig) -> bool:
        """Support both legacy and current optimization flags."""
        return runtime.optimize_storage or runtime.vacuum_after_run

    @staticmethod
    def _retention_hours(retention_days: int) -> int:
        """Convert retention policy from days to hours."""
        return retention_days * 24

    async def _optimize_tables(
        self,
        silver_table: str,
        gold_table: str,
        retention_hours: int,
        dry_run: bool,
    ) -> tuple[int, int]:
        """Vacuum Silver and Gold tables while avoiding duplicate targets.

        Postrun lifecycle maintenance must not prune Bronze files from the
        active run. Bronze retention remains an explicit maintenance action.

        Returns:
            Tuple of (silver_files_removed, gold_files_removed).
        """
        silver_removed = await self.storage.vacuum(
            table_name=silver_table,
            retention_hours=retention_hours,
            dry_run=dry_run,
        )
        if gold_table == silver_table:
            return int(silver_removed), 0
        gold_removed = await self.storage.vacuum(
            table_name=gold_table,
            retention_hours=retention_hours,
            dry_run=dry_run,
        )
        return int(silver_removed), int(gold_removed)

    @staticmethod
    def _emit_optimization_metric(
        metrics: MetricsPort | None,
        pipeline_name: str,
        status: str,
    ) -> None:
        """Emit optimization metric if metrics port is available."""
        if metrics:
            metrics.increment_counter(
                "bioetl_storage_optimization_total",
                1,
                {"pipeline": pipeline_name, "status": status},
            )


@dataclass
class MedallionLifecycleService(
    _MedallionRunLifecycleMixin, _MedallionMaintenanceMixin
):
    """Unified facade for managing medallion layer lifecycle operations."""

    storage: MedallionStorageProtocol
    logger: LoggerPort


__all__ = [
    "ClearResult",
    "MedallionLifecycleService",
    "PrepareResult",
    "VacuumResult",
]
