"""Postrun Service for post-execution operations."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
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
        otel_tracer = self._tracer.get_tracer(self.TRACER_NAME)
        with cast(
            "Span",
            otel_tracer.start_as_current_span(
                span_name,
                attributes={
                    "bioetl.pipeline": self._config.pipeline_name or "unknown",
                    "bioetl.provider": self._config.provider,
                    "bioetl.entity_type": self._config.entity_type,
                    "bioetl.run_type": self._runtime.run_type.value,
                },
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

    def _record_run_span_attributes(self, span: Span, result: PostrunResult) -> None:
        """Attach postrun outcome attributes to the active tracing span."""
        span.set_attribute("bioetl.dq_status", result.dq.status.value)

    def _run_dq_phase(self, executor: ExecutorMetricsPort) -> DQResult:
        """Execute data-quality evaluation for the completed run."""
        return self.run_dq_checks(executor)

    async def _run_compaction_phase(self) -> CompactionResult:
        """Execute the compaction phase for Silver when the policy allows it."""
        return await self.run_silver_compact_if_needed()

    async def _run_dq_report_phase(
        self,
        dq_context: DQReportContext | None,
    ) -> DQReportResult | None:
        """Generate postrun DQ reports for the current run."""
        return await self._generate_dq_reports(dq_context)

    async def _run_vacuum_phase(self) -> VacuumResult:
        """Execute VACUUM finalization for the current run."""
        return await self.run_vacuum_if_enabled()

    async def _run_final_metadata_phase(
        self,
        executor: ExecutorMetricsPort,
        dq_reports: DQReportResult | None,
    ) -> None:
        """Persist final metadata when metadata collaborators are configured."""
        await self._metadata_write_orchestrator.write_final_metadata_if_available(
            executor,
            dq_reports,
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
