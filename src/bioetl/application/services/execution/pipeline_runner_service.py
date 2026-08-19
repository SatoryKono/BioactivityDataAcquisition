"""Pipeline runner service for universal pipeline execution.

Provides a high-level, interface-agnostic API for running pipelines.
Can be used from CLI, REST API, Airflow operators, or any other orchestrator.

Implements RULES.md §1.1 - Application Layer depends only on Domain.
"""

from __future__ import annotations

__all__ = [
    "PipelineNotFoundError",
    "PipelineRunResult",
    "PipelineRunnerService",
    "RunOptions",
    "RunResult",
]


from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.application.services.execution._pipeline_runner_support import (
    build_dry_run_result,
    build_pipeline_run_result,
    complete_pipeline_dry_run,
    create_execution_runner_audited,
)
from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineExecutionResult,
    PipelineRunExecutionService,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.context import (
    bind_stage_accounting,
    reset_stage_accounting,
)
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        ClockPort,
        ExecutionMetricsRunnerPort,
        LoggerPort,
        MetricsExtractorPort,
        MetricsPort,
        RunnerFactoryPort,
    )


async def _record_pipeline_audit_event(
    audit: AuditPort,
    *,
    event_name: str,
    pipeline_name: str,
    run_id: RunID,
    run_type: str,
    status: str,
    timestamp: datetime,
    manifest_id: str | None = None,
    error_type: str | None = None,
) -> None:
    """Record pipeline lifecycle outcome via the audit port abstraction."""
    event_data = {
        "pipeline": pipeline_name,
        "run_id": str(run_id),
        "run_type": run_type,
        "status": status,
    }
    if manifest_id is not None:
        event_data["manifest_id"] = manifest_id
    if error_type is not None:
        event_data["error_type"] = error_type
    await audit.log_event(event_name, event_data, timestamp=timestamp)


def _resolve_effective_run_id(
    *,
    run_id: UUID | None,
    options: RunOptions,
    run_id_factory: Callable[[], RunID | UUID | str],
) -> RunID:
    if run_id is not None:
        return cast(RunID, run_id)
    if options.exact_replay:
        raise ValueError("exact replay requires explicit run_id")
    generated_run_id = run_id_factory()
    if isinstance(generated_run_id, UUID):
        return cast(RunID, generated_run_id)
    return cast(RunID, UUID(str(generated_run_id)))


def _missing_run_id_factory() -> RunID:
    raise RuntimeError("pipeline run_id_factory must be supplied by composition root")


@dataclass
class PipelineRunnerService:
    """Interface-agnostic application service for pipeline execution."""

    runner_factory: RunnerFactoryPort
    metrics_extractor: MetricsExtractorPort
    logger: LoggerPort
    metrics: MetricsPort
    audit: AuditPort
    clock: ClockPort
    _context_service: PipelineRunContextService
    _execution_service: PipelineRunExecutionService
    run_id_factory: Callable[[], RunID | UUID | str] = _missing_run_id_factory

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: UUID | None = None,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Run a pipeline and return normalized execution result.

        Args:
            pipeline_name: Registered pipeline identifier to execute.
            dry_run: If True, validate and plan but skip storage writes.
                Overridden by options.dry_run if options is provided.
            run_id: Optional explicit UUID for the run. Required for exact replay
                and auto-generated only for operational runtime paths.
            options: Optional RunOptions controlling run type, limit, filters, etc.
                If None, a default RunOptions instance is created using dry_run.

        Returns:
            RunResult with status, record counts, duration, and error details.

        Raises:
            PipelineNotFoundError: If pipeline_name is not registered in the factory.
        """
        started_at, started_monotonic = capture_runtime_timing_anchor(
            clock=self.clock,
            started_at=self.clock.now(),
        )
        effective_options = self._merge_options(options, dry_run)
        self._ensure_pipeline_exists(pipeline_name)
        effective_run_id = _resolve_effective_run_id(
            run_id=run_id,
            options=effective_options,
            run_id_factory=self.run_id_factory,
        )
        context = self._build_context(
            pipeline_name,
            effective_run_id,
            effective_options,
            started_at=started_at,
        )
        run_logger = self._create_run_logger(
            context=context,
            options=effective_options,
        )
        await _record_pipeline_audit_event(
            self.audit,
            event_name="PipelineRunStarted",
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            run_type=effective_options.run_type,
            status="started",
            timestamp=started_at,
        )
        dry_run_result = self._maybe_dry_run_result(
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            run_logger=run_logger,
        )
        if dry_run_result is not None:
            return await complete_pipeline_dry_run(
                audit=self.audit,
                pipeline_name=pipeline_name,
                run_id=effective_run_id,
                options=effective_options,
                dry_run_result=dry_run_result,
                record_event=_record_pipeline_audit_event,
            )

        async def _record_constructor_failure(exc: Exception) -> None:
            await _record_pipeline_audit_event(
                self.audit,
                event_name="PipelineRunCompleted",
                pipeline_name=pipeline_name,
                run_id=effective_run_id,
                run_type=effective_options.run_type,
                status="failed",
                timestamp=self.clock.now(),
                error_type=type(exc).__name__,
            )

        return await self._execute_prepared_run(
            context=context,
            run_logger=run_logger,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            started_monotonic=started_monotonic,
            record_constructor_failure=_record_constructor_failure,
        )

    async def _execute_prepared_run(
        self,
        *,
        context: object,
        run_logger: object,
        pipeline_name: str,
        run_id: UUID,
        options: RunOptions,
        started_at: object,
        started_monotonic: object,
        record_constructor_failure,
    ) -> RunResult:
        runner = await create_execution_runner_audited(
            lambda: _require_execution_runner(self.runner_factory.create(context)),
            record_failure=record_constructor_failure,
        )
        accounting = StageAccountingAccumulator()
        accounting_token = bind_stage_accounting(accounting)
        try:
            return await self._execute_pipeline(
                runner=runner,
                run_logger=run_logger,
                pipeline_name=pipeline_name,
                run_id=run_id,
                run_type=options.run_type,
                started_at=started_at,
                started_monotonic=started_monotonic,
                options=options,
            )
        finally:
            reset_stage_accounting(accounting_token)

    def _ensure_pipeline_exists(self, pipeline_name: str) -> None:
        if self.runner_factory.contains(pipeline_name):
            return
        available = self.runner_factory.list_pipelines()
        raise PipelineNotFoundError(pipeline_name, available)

    def _create_run_logger(
        self,
        *,
        context: PipelineRunContext,
        options: RunOptions,
    ) -> LoggerPort:
        run_logger = self.logger.bind(**context.log_correlation_fields())
        run_logger.info(
            "Starting pipeline run",
            run_type=options.run_type,
            dry_run=options.dry_run,
            limit=options.limit,
        )
        return run_logger

    def _maybe_dry_run_result(
        self,
        *,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
        started_at: datetime,
        run_logger: LoggerPort,
    ) -> RunResult | None:
        return build_dry_run_result(
            clock=self.clock,
            pipeline_name=pipeline_name,
            run_id=run_id,
            options=options,
            started_at=started_at,
            run_logger=run_logger,
        )

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        return self.runner_factory.list_pipelines()

    def validate_pipeline(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        return self.runner_factory.contains(pipeline_name)

    def _merge_options(
        self,
        options: RunOptions | None,
        dry_run: bool,
    ) -> RunOptions:
        """Merge individual parameters with RunOptions."""
        return self._context_service.merge_options(
            options=options,
            dry_run=dry_run,
            default_options_factory=lambda dry_run_value: RunOptions(
                dry_run=dry_run_value
            ),
        )

    def _build_context(
        self,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
        started_at: datetime,
    ) -> PipelineRunContext:
        """Build PipelineRunContext from options."""
        return self._context_service.build_context(
            pipeline_name=pipeline_name,
            run_id=run_id,
            options=options,
            started_at=started_at,
        )

    async def _execute_pipeline(
        self,
        runner: ExecutionMetricsRunnerPort,
        run_logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
        started_monotonic: float,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Execute pipeline and build normalized RunResult."""
        outcome = await self._execution_service.execute(
            runner=runner,
            run_logger=run_logger,
            metrics_extractor=self.metrics_extractor,
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        result = self._build_run_result(
            outcome=outcome,
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
            options=options,
        )
        # Terminal run counter is owned by PipelineObserver.__exit__.
        # Incrementing here double-counts every CLI/service run (OBS-LIFE-001).
        await _record_pipeline_audit_event(
            self.audit,
            event_name="PipelineRunCompleted",
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=run_type,
            status=result.status.value,
            timestamp=result.completed_at,
            manifest_id=result.manifest_id,
            error_type=result.error_type,
        )
        return result

    def _build_run_result(
        self,
        *,
        outcome: PipelineExecutionResult,
        runner: ExecutionMetricsRunnerPort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Convert execution outcome to public RunResult contract."""
        return build_pipeline_run_result(
            outcome=outcome,
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
            options=options,
        )


def _require_execution_runner(runner: object) -> ExecutionMetricsRunnerPort:
    """Validate producer output before pipeline side effects begin."""
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner
