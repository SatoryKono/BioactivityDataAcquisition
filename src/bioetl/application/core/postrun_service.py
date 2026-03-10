"""Postrun Service for post-execution operations."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.core.postrun_cleanup_orchestrator import (
    PostrunCleanupService,
)
from bioetl.application.core.postrun_compact_orchestrator import (
    PostrunCompactService,
)
from bioetl.application.core.postrun_dq_report_orchestrator import (
    PostrunDQReportService,
)
from bioetl.application.core.postrun_metadata_version_resolver import (
    PostrunMetadataVersionResolver,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_types import VacuumResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import ExecutorMetricsPort
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
        DQReportService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        SilverDQConfigPort,
        StorageMaintenancePort,
        TracingPort,
    )


def _create_postrun_cleanup_service(
    logger: LoggerPort,
    warning_allowlist: tuple[type[BaseException], ...],
) -> PostrunCleanupService:
    return PostrunCleanupService(
        logger=logger,
        warning_allowlist=warning_allowlist,
    )


def _create_postrun_dq_report_service(
    *,
    logger: LoggerPort,
    runtime: RuntimeConfig,
    dq_report_service: DQReportService | None,
    bronze_dq_config: BronzeDQConfigPort | None,
    silver_dq_config: SilverDQConfigPort | None,
    gold_dq_config: GoldDQConfigPort | None,
    warning_allowlist: tuple[type[BaseException], ...],
) -> PostrunDQReportService:
    return PostrunDQReportService(
        logger=logger,
        runtime=runtime,
        dq_report_service=dq_report_service,
        bronze_dq_config=bronze_dq_config,
        silver_dq_config=silver_dq_config,
        gold_dq_config=gold_dq_config,
        warning_allowlist=warning_allowlist,
    )


def _create_postrun_metadata_version_resolver(
    *,
    logger: LoggerPort,
    runtime: RuntimeConfig,
    warning_allowlist: tuple[type[BaseException], ...],
) -> PostrunMetadataVersionResolver:
    return PostrunMetadataVersionResolver(
        logger=logger,
        runtime=runtime,
        warning_allowlist=warning_allowlist,
    )


def _create_postrun_compact_service(
    *,
    config: PipelineConfig,
    storage: StorageMaintenancePort,
    logger: LoggerPort,
    warning_allowlist: tuple[type[BaseException], ...],
) -> PostrunCompactService:
    return PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=warning_allowlist,
    )


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations."""

    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult
    duplicates_removed: int = 0


class PostrunService:
    """Handles post-execution operations."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        context: PipelineContext,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        storage: StorageMaintenancePort,
        metrics: MetricsPort | None,
        logger: LoggerPort,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        dq_report_service: DQReportService | None = None,
        bronze_dq_config: BronzeDQConfigPort | None = None,
        silver_dq_config: SilverDQConfigPort | None = None,
        gold_dq_config: GoldDQConfigPort | None = None,
    ) -> None:
        """Initialize postrun service."""
        self._config = config
        self._runtime = runtime
        self._context = context
        self._dq_service = dq_service
        self._lifecycle_service = lifecycle_service
        self._storage = storage
        self._metrics = metrics
        self._logger = logger
        self._metadata_coordinator = metadata_coordinator
        self._metadata_writer = metadata_writer
        self._postrun_warning_allowlist = (
            BioETLError,
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
        )
        self._metadata_version_allowlist = (
            ImportError,
            ModuleNotFoundError,
            FileNotFoundError,
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
        )
        self._cleanup_orchestrator = _create_postrun_cleanup_service(
            logger=logger,
            warning_allowlist=self._postrun_warning_allowlist,
        )
        self._dq_report_orchestrator = _create_postrun_dq_report_service(
            logger=logger,
            runtime=runtime,
            dq_report_service=dq_report_service,
            bronze_dq_config=bronze_dq_config,
            silver_dq_config=silver_dq_config,
            gold_dq_config=gold_dq_config,
            warning_allowlist=self._postrun_warning_allowlist,
        )
        self._metadata_version_resolver = _create_postrun_metadata_version_resolver(
            logger=logger,
            runtime=runtime,
            warning_allowlist=self._metadata_version_allowlist,
        )
        self._compact_orchestrator = _create_postrun_compact_service(
            config=config,
            storage=storage,
            logger=logger,
            warning_allowlist=self._postrun_warning_allowlist,
        )

    async def run(
        self,
        executor: ExecutorMetricsPort,
        dq_context: DQReportContext | None = None,
    ) -> PostrunResult:
        """Run all post-execution operations.

        Args:
            executor: Provides batch metrics and record counts for DQ evaluation.
            dq_context: Optional context with table paths for DQ report generation.

        Returns:
            PostrunResult with DQ check results, DQ report paths, and vacuum stats.
        """
        # Silver compact before DQ so checks see deduplicated data
        duplicates_removed = await self.run_silver_compact_if_needed()

        dq_result = await self.run_dq_checks(executor)
        dq_reports = await self._generate_dq_reports(dq_context)
        vacuum_result = await self.run_vacuum_if_enabled()

        # Write final run-level metadata (aggregates all batches)
        if self._metadata_coordinator and self._metadata_writer:
            await self._write_final_metadata(executor, dq_reports)

        return PostrunResult(
            dq=dq_result,
            dq_reports=dq_reports,
            vacuum=vacuum_result,
            duplicates_removed=duplicates_removed,
        )

    async def run_dq_checks(self, executor: ExecutorMetricsPort) -> DQResult:
        """Check data quality metrics and report anomalies.

        Args:
            executor: Provides batch metrics and record counts for evaluation.

        Returns:
            DQResult with overall DQ status and per-check results.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return await self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Returns:
            VacuumResult with file removal counts, or skipped=True if vacuum disabled.
        """
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def run_silver_compact_if_needed(self) -> int:
        """Deduplicate Silver after append-mode run. Returns duplicates removed."""
        return await self._compact_orchestrator.run_if_needed()

    async def cleanup(self, tracer: TracingPort | None) -> None:
        """Cleanup all resources including observability.

        Args:
            tracer: Optional tracing provider to flush and close.
        """
        await self._cleanup_orchestrator.cleanup_tracer(tracer)

    async def _generate_dq_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports if enabled."""
        return await self._dq_report_orchestrator.generate_reports(context)

    async def _write_final_metadata(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Write final aggregated metadata for Silver and Gold layers."""
        from datetime import UTC, datetime

        if not self._metadata_coordinator or not self._metadata_writer:
            return

        import asyncio

        stats = self._get_run_statistics(executor)
        completed_at = datetime.now(UTC)
        write_coros = [
            coro
            for coro in (
                self._build_silver_metadata_write_coro(
                    stats=stats,
                    dq_reports=dq_reports,
                    completed_at=completed_at,
                ),
                self._build_gold_metadata_write_coro(
                    stats=stats,
                    dq_reports=dq_reports,
                    completed_at=completed_at,
                ),
            )
            if coro is not None
        ]
        if write_coros:
            await asyncio.gather(*write_coros)

    @staticmethod
    def _get_run_statistics(executor: ExecutorMetricsPort) -> dict[str, object]:
        """Collect optional run-level statistics from executor."""
        get_stats = getattr(executor, "get_run_statistics", None)
        if not callable(get_stats):
            return {}
        raw_stats = get_stats()
        if isinstance(raw_stats, dict):
            return raw_stats
        return {}

    def _resolve_report_path(
        self,
        dq_reports: DQReportResult | None,
        *,
        layer: str,
    ) -> str | None:
        """Resolve report path by layer from optional DQ report result."""
        if dq_reports is None:
            return None
        if layer == "silver":
            path = dq_reports.silver_report_path
        elif layer == "gold":
            path = dq_reports.gold_report_path
        else:
            return None
        return str(path) if path else None

    def _build_silver_metadata_write_coro(
        self,
        *,
        stats: dict[str, object],
        dq_reports: DQReportResult | None,
        completed_at: datetime,
    ) -> Awaitable[object] | None:
        """Build coroutine for writing final Silver metadata."""
        from bioetl.domain.ports import SilverMetadataInput

        if not self._metadata_coordinator or not self._metadata_writer:
            return None
        silver_table = self._config.table.silver_table
        if not silver_table:
            return None

        silver_path = self._storage.get_table_path(silver_table, layer="silver")
        version_after = self._resolve_delta_version(
            table_path=str(silver_path),
            layer="silver",
        )
        silver_input = SilverMetadataInput(
            table_path=str(silver_path),
            primary_keys=list(self._config.table.primary_keys),
            mode=self._config.table.silver_write_mode,
            total_records=cast("int | None", stats.get("records_silver")),
            source_batch_ids=cast("list[str] | None", stats.get("source_batch_ids")),
            version_after=version_after,
            dq_report_path=self._resolve_report_path(dq_reports, layer="silver"),
            started_at=self._context.started_at,
            completed_at=completed_at,
        )
        silver_metadata = self._metadata_coordinator.create_silver_metadata(
            silver_input
        )
        return self._metadata_writer.write_silver_metadata(
            str(silver_path),
            silver_metadata,
            provider=self._config.provider,
            entity=self._config.entity_type,
        )

    def _build_gold_metadata_write_coro(
        self,
        *,
        stats: dict[str, object],
        dq_reports: DQReportResult | None,
        completed_at: datetime,
    ) -> Awaitable[object] | None:
        """Build coroutine for writing final Gold metadata."""
        from bioetl.domain.ports import GoldMetadataInput

        if not self._metadata_coordinator or not self._metadata_writer:
            return None
        gold_table = self._config.table.gold_table
        if not gold_table:
            return None

        gold_path = self._storage.get_table_path(gold_table, layer="gold")
        gold_input = GoldMetadataInput(
            table_path=str(gold_path),
            table_name=gold_table,
            mode=self._config.table.gold_write_mode,
            total_records=cast("int | None", stats.get("records_gold")),
            dq_report_path=self._resolve_report_path(dq_reports, layer="gold"),
            completed_at=completed_at,
            gold_schema=self._config.gold_schema,
        )
        gold_metadata = self._metadata_coordinator.create_gold_metadata(gold_input)
        return self._metadata_writer.write_gold_metadata(
            str(gold_path),
            gold_metadata,
            provider=self._config.provider,
            entity=self._config.entity_type,
        )

    def _collect_batch_metrics(self, executor: ExecutorMetricsPort) -> dict[str, float]:
        """Collect batch metrics from executor."""
        total_records = max(1, executor.records_fetched)
        return {
            "record_count": float(executor.records_fetched),
            "bronze_count": float(executor.records_bronze),
            "silver_count": float(executor.records_silver),
            "gold_count": float(executor.records_gold),
            "quarantined_count": float(executor.records_quarantined),
            "error_rate": executor.records_quarantined / total_records,
            "silver_yield": executor.records_silver / total_records,
            "gold_yield": executor.records_gold / total_records,
        }

    def _resolve_delta_version(self, table_path: str, *, layer: str) -> int | None:
        """Resolve Delta table version with warning-mode fallback and allowlist."""
        return self._metadata_version_resolver.resolve_delta_version(
            table_path,
            layer=layer,
        )


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsPort",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
