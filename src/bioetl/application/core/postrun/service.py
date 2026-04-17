"""Postrun Service for post-execution operations."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as _RF005_OPERATION_ERRORS,
)
from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
)
from bioetl.application.core.span_helpers import (
    build_pipeline_span_attributes,
    start_current_span,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_types import VacuumResult
from bioetl.domain.ports import ExecutorMetricsPort
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.postrun.cleanup_orchestrator import (
        PostrunCleanupService,
    )
    from bioetl.application.core.postrun.compact_orchestrator import (
        CompactionResult,
        PostrunCompactService,
    )
    from bioetl.application.core.postrun.dq_report_orchestrator import (
        PostrunDQReportService,
    )
    from bioetl.application.core.postrun.metadata_write_service import (
        PostrunMetadataWriteService,
    )
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort


@dataclass(frozen=True, slots=True)
class PostrunResult:
    """Combined result of all post-run operations."""

    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult
    compaction: CompactionResult


@dataclass(frozen=True, slots=True)
class PostrunDependencyContext:
    """Injected postrun collaborators created by the composition layer."""

    cleanup_orchestrator: PostrunCleanupService
    dq_report_orchestrator: PostrunDQReportService
    metadata_write_orchestrator: PostrunMetadataWriteService
    compact_orchestrator: PostrunCompactService


class PostrunService:
    """Handles post-execution operations."""

    TRACER_NAME = "bioetl.postrun"
    METRIC_POSTRUN_PHASE_EVENTS_TOTAL = "bioetl_postrun_phase_events_total"
    METRIC_POSTRUN_PHASE_DURATION_SECONDS = "bioetl_postrun_phase_duration_seconds"
    OPERATION_ERRORS = _RF005_OPERATION_ERRORS

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        context: PipelineContext,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        dependencies: PostrunDependencyContext | None = None,
        services: PipelineService | None = None,
        tracer: TracingPort | None = None,
        **legacy_kwargs: object,
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._context = context
        self._dq_service = dq_service
        self._lifecycle_service = lifecycle_service
        if dependencies is None:
            raise AssertionError("dependencies must be provided")

        resolved_collaborators = resolve_postrun_collaborators(
            services=services,
            context=context,
            legacy_kwargs=legacy_kwargs,
        )
        self._metrics = resolved_collaborators.metrics
        self._logger = resolved_collaborators.logger
        self._cleanup_orchestrator = dependencies.cleanup_orchestrator
        self._dq_report_orchestrator = dependencies.dq_report_orchestrator
        self._metadata_write_orchestrator = dependencies.metadata_write_orchestrator
        self._compact_orchestrator = dependencies.compact_orchestrator
        if tracer is None:
            raise TypeError(
                "PostrunService requires explicit tracer injection. "
                "Build NoOpTracing in composition or test support when needed."
            )
        self._tracer = tracer

    @contextmanager
    def _postrun_span(self, span_name: str) -> Generator[Span, None, None]:
        """Context manager for OTel span lifecycle."""
        with start_current_span(
            tracing=self._tracer,
            tracer_name=self.TRACER_NAME,
            span_name=span_name,
            attributes=build_pipeline_span_attributes(
                config=self._config,
                runtime=self._runtime,
            ),
        ) as span:
            yield span

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
        with self._postrun_span("postrun.run") as span:
            result = await self._run_postrun_flow(
                executor=executor,
                dq_context=dq_context,
            )
            self._record_run_span_attributes(span, result)
            return result

    async def _run_postrun_flow(
        self,
        *,
        executor: ExecutorMetricsPort,
        dq_context: DQReportContext | None,
    ) -> PostrunResult:
        """Execute compaction, DQ, reporting, metadata, and vacuum in order."""
        compaction = await self._run_compaction_phase()
        dq_result = self._run_dq_phase(executor)
        dq_reports = await self._run_dq_report_phase(dq_context)
        vacuum_result = await self._run_vacuum_phase()
        await self._run_final_metadata_phase(executor, dq_reports)
        return PostrunResult(
            dq=dq_result,
            dq_reports=dq_reports,
            vacuum=vacuum_result,
            compaction=compaction,
        )

    def _emit_postrun_phase_observability(
        self,
        *,
        phase: Literal[
            "compaction",
            "dq_evaluation",
            "dq_reports",
            "vacuum",
            "final_metadata",
        ],
        status: str,
        duration_seconds: float,
        level: Literal["info", "warning", "error"] | None = None,
        **extra: object,
    ) -> None:
        """Emit bounded metrics and structured logs for one postrun subphase."""
        labels = {
            "pipeline": self._config.pipeline_name,
            "phase": phase,
            "status": status,
        }
        self._metrics.increment_counter(
            self.METRIC_POSTRUN_PHASE_EVENTS_TOTAL,
            1,
            labels=labels,
        )
        self._metrics.observe_histogram(
            self.METRIC_POSTRUN_PHASE_DURATION_SECONDS,
            duration_seconds,
            labels=labels,
        )

        resolved_level = level or self._resolve_postrun_phase_log_level(status)
        log_payload: dict[str, object] = {
            "phase": phase,
            "status": status,
            "duration_seconds": round(duration_seconds, 4),
            **extra,
        }
        if resolved_level == "error":
            self._logger.error("postrun_phase_completed", **log_payload)
        elif resolved_level == "warning":
            self._logger.warning("postrun_phase_completed", **log_payload)
        else:
            self._logger.info("postrun_phase_completed", **log_payload)

    @staticmethod
    def _resolve_postrun_phase_log_level(
        status: str,
    ) -> Literal["info", "warning", "error"]:
        """Map bounded postrun status values to structured log levels."""
        if status == "failed":
            return "error"
        if status == "warning":
            return "warning"
        return "info"

    def _record_run_span_attributes(self, span: Span, result: PostrunResult) -> None:
        """Attach postrun outcome attributes to the active tracing span."""
        span.set_attribute("bioetl.dq_status", result.dq.status.value)
        span.set_attribute("bioetl.dq_anomalies_count", result.dq.anomalies_count)
        span.set_attribute("bioetl.dq_has_critical", result.dq.has_critical)
        span.set_attribute("bioetl.dq_check_duration_ms", result.dq.check_duration_ms)
        span.set_attribute(
            "bioetl.dq_reports_generated",
            bool(result.dq_reports and result.dq_reports.any_generated),
        )
        span.set_attribute(
            "bioetl.dq_reports_count",
            0 if result.dq_reports is None else result.dq_reports.reports_count,
        )
        span.set_attribute("bioetl.compaction_status", result.compaction.status)
        span.set_attribute(
            "bioetl.compaction_duplicates_removed",
            result.compaction.duplicates_removed,
        )
        span.set_attribute("bioetl.vacuum_skipped", result.vacuum.skipped)
        span.set_attribute(
            "bioetl.vacuum_silver_files_removed",
            result.vacuum.silver_files_removed,
        )
        span.set_attribute(
            "bioetl.vacuum_gold_files_removed",
            result.vacuum.gold_files_removed,
        )

    def _run_dq_phase(self, executor: ExecutorMetricsPort) -> DQResult:
        """Execute data-quality evaluation for the completed run."""
        start_time = time.perf_counter()
        with self._postrun_span("postrun.dq_evaluation") as span:
            try:
                result = self.run_dq_checks(executor)
            except self.OPERATION_ERRORS as exc:
                self._emit_postrun_phase_observability(
                    phase="dq_evaluation",
                    status="failed",
                    duration_seconds=time.perf_counter() - start_time,
                    level="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute("bioetl.dq_status", result.status.value)
            span.set_attribute("bioetl.dq_anomalies_count", result.anomalies_count)
            span.set_attribute("bioetl.dq_has_critical", result.has_critical)
            span.set_attribute(
                "bioetl.dq_check_duration_ms",
                result.check_duration_ms,
            )
            self._emit_postrun_phase_observability(
                phase="dq_evaluation",
                status=result.status.value,
                duration_seconds=time.perf_counter() - start_time,
                anomalies_count=result.anomalies_count,
                has_critical=result.has_critical,
                check_duration_ms=result.check_duration_ms,
            )
            return result

    async def _run_compaction_phase(self) -> CompactionResult:
        """Execute the compaction phase for Silver when the policy allows it."""
        start_time = time.perf_counter()
        with self._postrun_span("postrun.compaction") as span:
            try:
                result = await self.run_silver_compact_if_needed()
            except self.OPERATION_ERRORS as exc:
                self._emit_postrun_phase_observability(
                    phase="compaction",
                    status="failed",
                    duration_seconds=time.perf_counter() - start_time,
                    level="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute("bioetl.compaction_status", result.status)
            span.set_attribute(
                "bioetl.compaction_duplicates_removed",
                result.duplicates_removed,
            )
            if result.error is not None:
                span.set_attribute("bioetl.compaction_error", result.error)
            self._emit_postrun_phase_observability(
                phase="compaction",
                status=result.status,
                duration_seconds=time.perf_counter() - start_time,
                level="warning" if result.status == "failed" else None,
                duplicates_removed=result.duplicates_removed,
                has_error=result.error is not None,
            )
            return result

    async def _run_dq_report_phase(
        self,
        dq_context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate postrun DQ reports for the current run."""
        start_time = time.perf_counter()
        with self._postrun_span("postrun.dq_reports") as span:
            try:
                result = await self._generate_dq_reports(dq_context)
            except self.OPERATION_ERRORS as exc:
                self._emit_postrun_phase_observability(
                    phase="dq_reports",
                    status="failed",
                    duration_seconds=time.perf_counter() - start_time,
                    level="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute(
                "bioetl.dq_reports_generated",
                bool(result and result.any_generated),
            )
            span.set_attribute(
                "bioetl.dq_reports_count",
                0 if result is None else result.reports_count,
            )
            self._emit_postrun_phase_observability(
                phase="dq_reports",
                status="generated" if result and result.any_generated else "skipped",
                duration_seconds=time.perf_counter() - start_time,
                reports_generated=bool(result and result.any_generated),
                reports_count=0 if result is None else result.reports_count,
            )
            return result

    async def _run_vacuum_phase(self) -> VacuumResult:
        """Execute VACUUM finalization for the current run."""
        start_time = time.perf_counter()
        with self._postrun_span("postrun.vacuum") as span:
            try:
                result = await self.run_vacuum_if_enabled()
            except self.OPERATION_ERRORS as exc:
                self._emit_postrun_phase_observability(
                    phase="vacuum",
                    status="failed",
                    duration_seconds=time.perf_counter() - start_time,
                    level="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute("bioetl.vacuum_skipped", result.skipped)
            span.set_attribute(
                "bioetl.vacuum_silver_files_removed",
                result.silver_files_removed,
            )
            span.set_attribute(
                "bioetl.vacuum_gold_files_removed",
                result.gold_files_removed,
            )
            self._emit_postrun_phase_observability(
                phase="vacuum",
                status="skipped" if result.skipped else "success",
                duration_seconds=time.perf_counter() - start_time,
                silver_files_removed=result.silver_files_removed,
                gold_files_removed=result.gold_files_removed,
                skipped=result.skipped,
            )
            return result

    async def _run_final_metadata_phase(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Persist final metadata when metadata collaborators are configured."""
        start_time = time.perf_counter()
        with self._postrun_span("postrun.final_metadata") as span:
            try:
                wrote_metadata = await self._metadata_write_orchestrator.write_final_metadata_if_available(
                    executor,
                    dq_reports,
                )
            except self.OPERATION_ERRORS as exc:
                self._emit_postrun_phase_observability(
                    phase="final_metadata",
                    status="failed",
                    duration_seconds=time.perf_counter() - start_time,
                    level="error",
                    error_type=type(exc).__name__,
                )
                raise
            span.set_attribute("bioetl.final_metadata_phase_completed", True)
            span.set_attribute(
                "bioetl.dq_reports_available",
                dq_reports is not None,
            )
            self._emit_postrun_phase_observability(
                phase="final_metadata",
                status="success" if wrote_metadata else "skipped",
                duration_seconds=time.perf_counter() - start_time,
                dq_reports_available=dq_reports is not None,
                metadata_written=wrote_metadata,
            )

    def run_dq_checks(self, executor: ExecutorMetricsPort) -> DQResult:
        """Check data quality metrics and report anomalies.

        Args:
            executor: Provides batch metrics and record counts for evaluation.

        Returns:
            DQResult with overall DQ status and per-check results.
        """
        batch_metrics = self._collect_batch_metrics(executor)
        return self._dq_service.evaluate(batch_metrics)

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

    async def run_silver_compact_if_needed(self) -> CompactionResult:
        """Deduplicate Silver after append-mode run."""
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
            "freshness_anchor_timestamp": self._context.started_at.timestamp(),
        }


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsPort",
    "PostrunDependencyContext",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
