# MRO/override residual on mixin or client hierarchies.
"""Postrun Service for post-execution operations."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)
from bioetl.application.core.pipeline_span_lifecycle import (
    build_pipeline_span_attributes,
    start_current_span,
)
from bioetl.application.core.postrun._phase_descriptions import (
    record_run_span_attributes,
)
from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
)
from bioetl.application.core.postrun._service_support import (
    PostrunServiceSupportMixin,
)
from bioetl.application.services.medallion.medallion_types import VacuumResult
from bioetl.application.services.quality.data_quality_service import DataQualityService
from bioetl.domain.ports import ExecutorMetricsPort
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.pipeline_service_protocols import (
        PipelinePostrunServicesProtocol,
    )
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
    from bioetl.application.services.medallion.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.quality.dq_report_service import (
        DQReportContext,
        DQReportResult,
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


class PostrunService(PostrunServiceSupportMixin):
    """Handles post-execution operations."""

    TRACER_NAME = "bioetl.postrun"
    METRIC_POSTRUN_PHASE_EVENTS_TOTAL = "bioetl_postrun_phase_events_total"
    METRIC_POSTRUN_PHASE_DURATION_SECONDS = "bioetl_postrun_phase_duration_seconds"
    OPERATION_ERRORS = SHARED_OPERATION_ERRORS

    # Host attrs are assigned in __init__; surface contract is _PostrunHostAttrSurface.

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        context: PipelineContext,
        dq_service: DataQualityService,
        lifecycle_service: MedallionLifecycleService,
        dependencies: PostrunDependencyContext | None = None,
        services: PipelinePostrunServicesProtocol | None = None,
        tracer: TracingPort | None = None,
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
    def _postrun_span(self, span_name: str) -> Generator[Span, None, None]:  # pyright: ignore[reportIncompatibleMethodOverride]
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
            record_run_span_attributes(span, result)
            return result

    async def _run_postrun_flow(
        self,
        *,
        executor: ExecutorMetricsPort,
        dq_context: DQReportContext | None,
    ) -> PostrunResult:
        """Execute compaction, DQ, reporting, metadata, and vacuum in order."""
        host = cast(Any, self)  # Any: phased postrun methods are supplied by mixins
        compaction = await host._run_compaction_phase()
        dq_result = host._run_dq_phase(executor)
        dq_reports = await host._run_dq_report_phase(dq_context)
        vacuum_result = await host._run_vacuum_phase()
        await host._run_final_metadata_phase(executor, dq_reports)
        return PostrunResult(
            dq=dq_result,
            dq_reports=dq_reports,
            vacuum=vacuum_result,
            compaction=compaction,
        )


__all__ = [
    "DQEvaluationStatus",
    "DQResult",
    "ExecutorMetricsPort",
    "PostrunDependencyContext",
    "PostrunResult",
    "PostrunService",
    "VacuumResult",
]
