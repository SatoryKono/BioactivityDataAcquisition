"""Private support mixin for PostrunService phase and cleanup helpers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from bioetl.application.core.postrun._phase_descriptions import (
    PostrunLogLevel,
    describe_compaction_phase,
    describe_dq_phase,
    describe_dq_report_phase,
    describe_final_metadata_phase,
    describe_vacuum_phase,
)
from bioetl.application.core.postrun._phase_runtime import (
    PostrunPhaseName,
    emit_postrun_phase_observability,
    run_async_postrun_phase,
    run_sync_postrun_phase,
)
from bioetl.domain.ports import (
    ExecutorMetricsPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.value_objects.dq_result import DQResult

if TYPE_CHECKING:
    from opentelemetry.trace import Span

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
    from bioetl.application.services.data_quality_service import DataQualityService
    from bioetl.application.services.dq_report_service import (
        DQReportContext,
        DQReportResult,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.medallion_types import VacuumResult
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext


class PostrunServiceSupportMixin:
    """Own thin phase execution helpers outside the main postrun shell."""

    _config: PipelineConfig
    _runtime: RuntimeConfig
    _context: PipelineContext
    _dq_service: DataQualityService
    _lifecycle_service: MedallionLifecycleService
    _compact_orchestrator: PostrunCompactService
    _cleanup_orchestrator: PostrunCleanupService
    _dq_report_orchestrator: PostrunDQReportService
    _metadata_write_orchestrator: PostrunMetadataWriteService
    _logger: LoggerPort
    _metrics: MetricsPort
    _postrun_span: Callable[[str], AbstractContextManager[Span]]
    OPERATION_ERRORS: tuple[type[BaseException], ...]
    METRIC_POSTRUN_PHASE_EVENTS_TOTAL: str
    METRIC_POSTRUN_PHASE_DURATION_SECONDS: str

    def _emit_postrun_phase_observability(
        self,
        *,
        phase: PostrunPhaseName,
        status: str,
        duration_seconds: float,
        level: PostrunLogLevel | None = None,
        **extra: object,
    ) -> None:
        emit_postrun_phase_observability(
            metrics=self._metrics,
            logger=self._logger,
            pipeline_name=self._config.pipeline_name,
            phase_events_metric=self.METRIC_POSTRUN_PHASE_EVENTS_TOTAL,
            phase_duration_metric=self.METRIC_POSTRUN_PHASE_DURATION_SECONDS,
            phase=phase,
            status=status,
            duration_seconds=duration_seconds,
            level=level,
            **extra,
        )

    def _run_dq_phase(self, executor: ExecutorMetricsPort) -> DQResult:
        return run_sync_postrun_phase(
            span_factory=self._postrun_span,
            phase="dq_evaluation",
            operation=lambda: self.run_dq_checks(executor),
            operation_errors=self.OPERATION_ERRORS,
            emit_phase_observability=self._emit_postrun_phase_observability,
            on_success=describe_dq_phase,
        )

    async def _run_compaction_phase(self) -> CompactionResult:
        return await run_async_postrun_phase(
            span_factory=self._postrun_span,
            phase="compaction",
            operation=self.run_silver_compact_if_needed,
            operation_errors=self.OPERATION_ERRORS,
            emit_phase_observability=self._emit_postrun_phase_observability,
            on_success=describe_compaction_phase,
        )

    async def _run_dq_report_phase(
        self,
        dq_context: DQReportContext | None,
    ) -> DQReportResult | None:
        return await run_async_postrun_phase(
            span_factory=self._postrun_span,
            phase="dq_reports",
            operation=lambda: self._generate_dq_reports(dq_context),
            operation_errors=self.OPERATION_ERRORS,
            emit_phase_observability=self._emit_postrun_phase_observability,
            on_success=describe_dq_report_phase,
        )

    async def _run_vacuum_phase(self) -> VacuumResult:
        return await run_async_postrun_phase(
            span_factory=self._postrun_span,
            phase="vacuum",
            operation=self.run_vacuum_if_enabled,
            operation_errors=self.OPERATION_ERRORS,
            emit_phase_observability=self._emit_postrun_phase_observability,
            on_success=describe_vacuum_phase,
        )

    async def _run_final_metadata_phase(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        async def _write_final_metadata() -> bool:
            return await self._metadata_write_orchestrator.write_final_metadata_if_available(
                executor,
                dq_reports,
            )

        await run_async_postrun_phase(
            span_factory=self._postrun_span,
            phase="final_metadata",
            operation=_write_final_metadata,
            operation_errors=self.OPERATION_ERRORS,
            emit_phase_observability=self._emit_postrun_phase_observability,
            on_success=lambda wrote_metadata: describe_final_metadata_phase(
                wrote_metadata=wrote_metadata,
                dq_reports=dq_reports,
            ),
        )

    def run_dq_checks(self, executor: ExecutorMetricsPort) -> DQResult:
        batch_metrics = self._collect_batch_metrics(executor)
        return self._dq_service.evaluate(batch_metrics)

    async def run_vacuum_if_enabled(self) -> VacuumResult:
        return await self._lifecycle_service.finalize_run(
            config=self._config,
            runtime=self._runtime,
            metrics=self._metrics,
        )

    async def run_silver_compact_if_needed(self) -> CompactionResult:
        return await self._compact_orchestrator.run_if_needed()

    async def cleanup(self, tracer: TracingPort | None) -> None:
        await self._cleanup_orchestrator.cleanup_tracer(tracer)

    async def _generate_dq_reports(
        self,
        context: DQReportContext | None,
    ) -> DQReportResult | None:
        return await self._dq_report_orchestrator.generate_reports(context)

    def _collect_batch_metrics(self, executor: ExecutorMetricsPort) -> dict[str, float]:
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
