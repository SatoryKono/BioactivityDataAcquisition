"""Postrun Service for post-execution operations.

Application Service that handles post-pipeline execution tasks:
- Data quality checks (delegated to DataQualityService)
- DQ report generation (delegated to DQReportService)
- VACUUM operations (delegated to MedallionLifecycleService)
- Tracer cleanup

Extracted from PipelineRunner to follow Single Responsibility Principle.
DQ logic further extracted to DataQualityService (SRP refactoring).
DQ report generation added for detailed data quality analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.core.postrun_cleanup_orchestrator import (
    PostrunCleanupService,
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


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations.

    Attributes:
        dq: Data quality evaluation result.
        dq_reports: DQ report generation result (optional).
        vacuum: VACUUM operation result.
    """

    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult


class PostrunService:
    """Handles post-execution operations.

    Responsibilities:
    - Orchestrating DQ checks via DataQualityService
    - DQ report generation via DQReportService (optional)
    - VACUUM operations via MedallionLifecycleService
    - Tracer cleanup

    Attributes:
        _config: Pipeline configuration.
        _runtime: Runtime configuration.
        _context: Pipeline execution context.
        _dq_service: Data quality service for DQ checks.
        _lifecycle_service: Medallion lifecycle service for VACUUM.
        _storage: Storage port for path resolution.
        _metrics: Optional metrics port.
        _logger: Structured logger.
        _cleanup_orchestrator: Tracer cleanup orchestration helper.
        _dq_report_orchestrator: DQ report generation orchestration helper.
        _metadata_version_resolver: Delta version resolution helper.
        _dq_report_service: Optional DQ report service for report generation.
        _bronze_dq_config: Optional Bronze DQ report configuration.
        _silver_dq_config: Optional Silver DQ report configuration.
        _gold_dq_config: Optional Gold DQ report configuration.
        _metadata_coordinator: Centralized metadata coordinator.
        _metadata_writer: Metadata sidecar file writer.
    """

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
        # DQ Report parameters (optional)
        dq_report_service: DQReportService | None = None,
        bronze_dq_config: BronzeDQConfigPort | None = None,
        silver_dq_config: SilverDQConfigPort | None = None,
        gold_dq_config: GoldDQConfigPort | None = None,
    ) -> None:
        """Initialize postrun service.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            context: Pipeline execution context.
            dq_service: Data quality service for DQ checks.
            lifecycle_service: Medallion lifecycle service for VACUUM.
            storage: Storage port for path resolution.
            metrics: Optional metrics port.
            logger: Structured logger.
            metadata_coordinator: Centralized metadata coordinator.
            metadata_writer: Metadata sidecar file writer.
            dq_report_service: Optional DQ report service for report generation.
            bronze_dq_config: Optional Bronze DQ report configuration.
            silver_dq_config: Optional Silver DQ report configuration.
            gold_dq_config: Optional Gold DQ report configuration.
        """
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
        # DQ Report services
        self._dq_report_service = dq_report_service
        self._bronze_dq_config = bronze_dq_config
        self._silver_dq_config = silver_dq_config
        self._gold_dq_config = gold_dq_config
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

    async def run(
        self,
        executor: ExecutorMetricsPort,
        dq_context: DQReportContext | None = None,
    ) -> PostrunResult:
        """Run all post-execution operations.

        Performs DQ checks, DQ report generation, and VACUUM in sequence.

        Args:
            executor: Pipeline executor with batch metrics.
            dq_context: Optional DQ report context with data and metadata.

        Returns:
            PostrunResult with DQ, DQ reports, and VACUUM results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        dq_result = await self.run_dq_checks(executor)
        dq_reports = await self._generate_dq_reports(dq_context)
        vacuum_result = await self.run_vacuum_if_enabled()

        # Write final run-level metadata (aggregates all batches)
        if self._metadata_coordinator and self._metadata_writer:
            await self._write_final_metadata(executor, dq_reports)

        return PostrunResult(dq=dq_result, dq_reports=dq_reports, vacuum=vacuum_result)

    async def run_dq_checks(self, executor: ExecutorMetricsPort) -> DQResult:
        """Check data quality metrics and report anomalies.

        Delegates to DataQualityService for threshold checks and anomaly detection.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            DQResult with evaluation results.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return await self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        """Run VACUUM on Silver and Gold tables if enabled.

        Delegates to MedallionLifecycleService.finalize_run() which handles:
        - Checking if vacuum is enabled
        - Skipping in dry-run mode
        - Vacuuming both Silver and Gold tables
        - Metrics emission

        Returns:
            VacuumResult with operation details.
        """
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def cleanup(self, tracer: TracingPort | None) -> None:
        """Cleanup all resources including observability.

        Ensures tracer spans are flushed before shutdown (O3).
        Handles errors gracefully to avoid masking pipeline exceptions.

        Args:
            tracer: Optional tracing port to close.
        """
        await self._cleanup_orchestrator.cleanup_tracer(tracer)

    async def _generate_dq_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate DQ reports if enabled.

        Delegates to DQReportService for generating Bronze, Silver, and Gold
        DQ reports based on configuration.

        Args:
            context: DQ report context with data and metadata.

        Returns:
            DQReportResult with paths to generated reports, or None if:
            - DQ report service is not available
            - No context provided
            - No reports are enabled in configuration
        """
        return await self._dq_report_orchestrator.generate_reports(context)

    async def _write_final_metadata(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Write final aggregated metadata for Silver and Gold layers.

        Aggregates statistics from all batches processed by the executor
        and writes a final run-level metadata sidecar file.

        Args:
            executor: Pipeline executor with accumulated metrics.
            dq_reports: Results from DQ report generation (for cross-links).
        """
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
    ) -> object | None:
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
            total_records=stats.get("records_silver"),
            source_batch_ids=stats.get("source_batch_ids"),
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
    ) -> object | None:
        """Build coroutine for writing final Gold metadata."""
        from bioetl.domain.ports import GoldMetadataInput

        if not self._metadata_coordinator or not self._metadata_writer:
            return None
        gold_table = self._config.table.gold_table
        if not gold_table:
            return None

        gold_path = self._storage.get_table_path(gold_table, layer="gold")
        version_after = self._resolve_delta_version(
            table_path=str(gold_path),
            layer="gold",
        )
        gold_input = GoldMetadataInput(
            table_path=str(gold_path),
            table_name=gold_table,
            mode=self._config.table.gold_write_mode,
            total_records=stats.get("records_gold"),
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
        """Collect batch metrics from executor.

        Args:
            executor: Pipeline executor with batch metrics.

        Returns:
            Dictionary of metric names to values.
        """
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
