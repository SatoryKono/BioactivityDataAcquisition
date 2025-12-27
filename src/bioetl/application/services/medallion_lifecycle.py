"""Medallion lifecycle service (Application layer - orchestration).

Implements RULES.md §2.1-2.3 medallion architecture lifecycle operations.
This service manages clearing, vacuum, and future archive operations.

Observability:
- Tracing: Spans for clear/vacuum/archive operations via traced_operation
- Metrics: medallion_clear_records_total, medallion_vacuum_files_total,
           medallion_vacuum_duration_seconds, medallion_archive_files_total
- Logging: Structured logs for all operations
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.observability.span_context import traced_operation

if TYPE_CHECKING:
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.ports import LoggerPort, MetricsPort, StoragePort, TracingPort


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


@dataclass
class MedallionLifecycleService:
    """Service for managing medallion layer lifecycle operations.

    Responsibilities:
    - Clear Silver/Gold tables based on policy (M5)
    - Vacuum, archive, optimize operations
    - Publish metrics for all operations

    This service is injected into PipelineRunner and handles
    lifecycle operations that were previously inline in the runner.

    Attributes:
        storage: StoragePort for data layer operations.
        logger: Structured logger for observability.
        metrics: Optional MetricsPort for publishing operation metrics.
        tracer: Optional TracingPort for distributed tracing.

    Example:
        >>> service = MedallionLifecycleService(storage=storage, logger=logger)
        >>> policy = MedallionPolicy.for_run_type(RunType.REBUILD)
        >>> result = await service.clear(
        ...     policy=policy,
        ...     silver_table="chembl_activity",
        ...     gold_table="chembl.activity",
        ...     dry_run=False,
        ... )
        >>> print(f"Cleared {result.total_cleared} records")

    Observability:
        When metrics port is provided, publishes:
        - medallion_clear_records_total: Counter of cleared records by layer
        - medallion_clear_duration_seconds: Histogram of clear operation duration
        - medallion_vacuum_files_total: Counter of vacuumed files
        - medallion_vacuum_duration_seconds: Histogram of vacuum duration
        - medallion_archive_files_total: Counter of archived files
    """

    storage: StoragePort
    logger: LoggerPort
    metrics: MetricsPort | None = field(default=None)
    tracer: TracingPort | None = field(default=None)

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
        - Publishes metrics if metrics port is available
        - Creates tracing span if tracer is available

        Args:
            policy: Medallion policy determining what to clear.
            silver_table: Silver table name.
            gold_table: Gold table name.
            dry_run: If True, only count without deleting.

        Returns:
            ClearResult with counts of cleared records.
        """
        async with traced_operation(
            self.tracer,
            "medallion.clear",
            tracer_name="bioetl.lifecycle",
            policy=policy.clear_policy.value,
            silver_table=silver_table,
            gold_table=gold_table,
            dry_run=dry_run,
        ):
            start_time = time.monotonic()
            silver_cleared = 0
            gold_cleared = 0

            if policy.should_clear_silver:
                silver_cleared = await self.storage.clear_silver(
                    silver_table, dry_run=dry_run
                )

            if policy.should_clear_gold:
                gold_cleared = await self.storage.clear_gold(
                    gold_table, dry_run=dry_run
                )

            result = ClearResult(
                silver_cleared=silver_cleared,
                gold_cleared=gold_cleared,
                dry_run=dry_run,
            )

            duration = time.monotonic() - start_time
            self._log_result(policy, silver_table, gold_table, result)
            self._record_clear_metrics(
                policy, silver_table, gold_table, result, duration
            )

            return result

    def _record_clear_metrics(
        self,
        policy: MedallionPolicy,
        silver_table: str,
        gold_table: str,
        result: ClearResult,
        duration: float,
    ) -> None:
        """Record clear operation metrics if metrics port is available."""
        if self.metrics is None or result.dry_run:
            return

        # Record duration histogram
        self.metrics.observe_histogram(
            "medallion_clear_duration_seconds",
            duration,
            {"policy": policy.clear_policy.value},
        )

        # Record cleared records counters
        if result.silver_cleared > 0:
            self.metrics.increment_counter(
                "medallion_clear_records_total",
                result.silver_cleared,
                {"layer": "silver", "table": silver_table},
            )

        if result.gold_cleared > 0:
            self.metrics.increment_counter(
                "medallion_clear_records_total",
                result.gold_cleared,
                {"layer": "gold", "table": gold_table},
            )

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
        async with traced_operation(
            self.tracer,
            "medallion.vacuum",
            tracer_name="bioetl.lifecycle",
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        ):
            retention_hours = retention_days * 24
            start_time = time.monotonic()

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

                duration = time.monotonic() - start_time

                self.logger.info(
                    "Vacuum completed",
                    table=table,
                    files_removed=files_removed,
                    dry_run=dry_run,
                    duration_seconds=round(duration, 3),
                )

                # Record metrics (only for actual operations, not dry runs)
                if self.metrics is not None and not dry_run:
                    self.metrics.observe_histogram(
                        "medallion_vacuum_duration_seconds",
                        duration,
                        {"table": table},
                    )
                    if files_removed > 0:
                        self.metrics.increment_counter(
                            "medallion_vacuum_files_total",
                            files_removed,
                            {"table": table},
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
        async with traced_operation(
            self.tracer,
            "medallion.archive",
            tracer_name="bioetl.lifecycle",
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        ):
            start_time = time.monotonic()

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

                duration = time.monotonic() - start_time

                self.logger.info(
                    "Archive completed",
                    table=table,
                    files_archived=files_archived,
                    duration_seconds=round(duration, 3),
                )

                # Record metrics
                if self.metrics is not None and files_archived > 0:
                    self.metrics.increment_counter(
                        "medallion_archive_files_total",
                        files_archived,
                        {"table": table},
                    )

                return files_archived

            except Exception as e:
                self.logger.error(
                    "Archive failed",
                    table=table,
                    error=str(e),
                )
                raise
