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
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_types import VacuumResult
from bioetl.domain.exceptions import BioETLError
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
        StoragePort,
        TracingPort,
    )


@runtime_checkable
class ExecutorMetricsPort(Protocol):
    """Protocol for executors providing batch metrics.

    Both PipelineExecutor and BatchExecutor implement this protocol.
    """

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


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
        storage: StoragePort,
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
        if tracer is not None:
            try:
                tracer.close()
                self._logger.debug("Tracer closed successfully")
            except self._postrun_warning_allowlist as e:
                self._logger.warning(
                    "Failed to close tracer",
                    error=str(e),
                    error_type=type(e).__name__,
                    reason="tracer_close_failed",
                )

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
        if self._dq_report_service is None:
            return None

        if context is None:
            self._logger.debug(
                "dq_report_skipped",
                reason="no context provided",
            )
            return None

        try:
            result = await self._dq_report_service.generate_reports(
                context=context,
                bronze_config=self._bronze_dq_config,
                silver_config=self._silver_dq_config,
                gold_config=self._gold_dq_config,
            )

            if result.any_generated:
                self._logger.info(
                    "dq_reports_completed",
                    reports_count=result.reports_count,
                    bronze_enabled=result.bronze_enabled,
                    silver_enabled=result.silver_enabled,
                    gold_enabled=result.gold_enabled,
                )

            return result

        except self._postrun_warning_allowlist as e:
            if self._runtime.strict_validation:
                self._logger.error(
                    "dq_report_generation_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    reason="dq_report_generation_failed_strict_mode",
                    strict_mode=True,
                )
                raise
            self._logger.warning(
                "dq_report_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
                reason="dq_report_generation_failed_warning_mode",
                strict_mode=False,
            )
            return None

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

        from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput

        # Get run-level statistics from executor
        stats = {}
        if hasattr(executor, "get_run_statistics"):
            stats = executor.get_run_statistics()

        if not self._metadata_coordinator or not self._metadata_writer:
            return

        # 1. Write final Silver metadata
        silver_table = self._config.table.silver_table
        if silver_table:
            silver_path = self._storage.get_table_path(silver_table)

            # Get Delta version for lineage (REQ-LINEAGE-002)
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
                dq_report_path=str(dq_reports.silver_report_path)
                if dq_reports and dq_reports.silver_report_path
                else None,
                started_at=self._context.started_at,
                completed_at=datetime.now(UTC),
            )
            silver_metadata = self._metadata_coordinator.create_silver_metadata(
                silver_input
            )
            await self._metadata_writer.write_silver_metadata(
                str(silver_path),
                silver_metadata,
                provider=self._config.provider,
                entity=self._config.entity_type,
            )

        # 2. Write final Gold metadata
        gold_table = self._config.table.gold_table
        if gold_table:
            gold_path = self._storage.get_table_path(gold_table)

            # Get Delta version
            version_after = self._resolve_delta_version(
                table_path=str(gold_path),
                layer="gold",
            )

            gold_input = GoldMetadataInput(
                table_path=str(gold_path),
                table_name=gold_table,
                mode=self._config.table.gold_write_mode,
                total_records=stats.get("records_gold"),
                dq_report_path=str(dq_reports.gold_report_path)
                if dq_reports and dq_reports.gold_report_path
                else None,
                completed_at=datetime.now(UTC),
                gold_schema=self._config.gold_schema,
            )
            gold_metadata = self._metadata_coordinator.create_gold_metadata(gold_input)
            await self._metadata_writer.write_gold_metadata(
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
        try:
            from deltalake import DeltaTable
            from deltalake.exceptions import DeltaError, TableNotFoundError

            dt = DeltaTable(table_path)
            return dt.version()
        except (ImportError, ModuleNotFoundError) as version_error:
            if self._runtime.strict_validation:
                self._logger.error(
                    "delta_version_resolution_failed",
                    layer=layer,
                    table_path=table_path,
                    error_type=type(version_error).__name__,
                    error=str(version_error),
                    reason="delta_dependency_missing_strict_mode",
                    strict_mode=True,
                )
                raise
            self._logger.warning(
                "delta_version_resolution_failed",
                layer=layer,
                table_path=table_path,
                error_type=type(version_error).__name__,
                error=str(version_error),
                reason="delta_dependency_missing_warning_mode",
                strict_mode=False,
            )
            return None
        except (TableNotFoundError, DeltaError) as version_error:
            if self._runtime.strict_validation:
                self._logger.error(
                    "delta_version_resolution_failed",
                    layer=layer,
                    table_path=table_path,
                    error_type=type(version_error).__name__,
                    error=str(version_error),
                    reason="delta_table_resolution_failed_strict_mode",
                    strict_mode=True,
                )
                raise
            self._logger.warning(
                "delta_version_resolution_failed",
                layer=layer,
                table_path=table_path,
                error_type=type(version_error).__name__,
                error=str(version_error),
                reason="delta_table_resolution_failed_warning_mode",
                strict_mode=False,
            )
            return None
        except self._metadata_version_allowlist as version_error:
            if self._runtime.strict_validation:
                self._logger.error(
                    "delta_version_resolution_failed",
                    layer=layer,
                    table_path=table_path,
                    error_type=type(version_error).__name__,
                    error=str(version_error),
                    reason="delta_version_resolution_failed_strict_mode",
                    strict_mode=True,
                )
                raise
            self._logger.warning(
                "delta_version_resolution_failed",
                layer=layer,
                table_path=table_path,
                error_type=type(version_error).__name__,
                error=str(version_error),
                reason="delta_version_resolution_failed_warning_mode",
                strict_mode=False,
            )
            return None


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsPort",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
