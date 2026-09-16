"""Pipeline runner service for universal pipeline execution.

Provides a high-level, interface-agnostic API for running pipelines.
Can be used from CLI, REST API, Airflow operators, or any other orchestrator.

Implements RULES.md Â§1.1 - Application Layer depends only on Domain.
"""

from __future__ import annotations

import asyncio

from bioetl.application.services.run_reports.control_plane_snapshot import (
    capture_run_completion,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    reset_run_observations,
)
from bioetl.domain.ports import RunReportStorePort

__all__ = [
    "PipelineNotFoundError",
    "PipelineRunResult",
    "PipelineRunnerService",
    "RunOptions",
    "RunResult",
]


from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.application.services.execution._pipeline_runner_support import (
    _require_execution_runner,
    build_dry_run_result,
    build_pipeline_run_result,
    complete_pipeline_dry_run,
    constructor_failure_recorder,
    create_execution_runner_audited,
    finalize_pipeline_run_report,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    missing_run_id_factory as _missing_run_id_factory,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    record_pipeline_audit_event as _record_pipeline_audit_event,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    resolve_effective_run_id as _resolve_effective_run_id,
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
    report_store: RunReportStorePort
    run_id_factory: Callable[[], RunID | UUID | str] = _missing_run_id_factory
    report_root: Path | None = None
    capture_control_plane: Callable[[str, str, datetime], None] | None = None

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: UUID | None = None,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Run a registered pipeline and return a normalized ``RunResult``."""
        started_at, started_monotonic = capture_runtime_timing_anchor(
            clock=self.clock,
            started_at=self.clock.now(),
        )
        effective_options = self._context_service.merge_options(
            options=options,
            dry_run=dry_run,
            default_options_factory=lambda dry_run_value: RunOptions(
                dry_run=dry_run_value
            ),
        )
        self._ensure_pipeline_exists(pipeline_name)
        effective_run_id = _resolve_effective_run_id(
            run_id=run_id,
            options=effective_options,
            run_id_factory=self.run_id_factory,
        )
        context = self._context_service.build_context(
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
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
        dry_run_result = build_dry_run_result(
            clock=self.clock,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            run_logger=run_logger,
        )
        if dry_run_result is not None:
            completed_dry_run = await complete_pipeline_dry_run(
                audit=self.audit,
                pipeline_name=pipeline_name,
                run_id=effective_run_id,
                options=effective_options,
                dry_run_result=dry_run_result,
                record_event=_record_pipeline_audit_event,
            )
            return self._finalize_report(completed_dry_run, effective_options)

        record_constructor_failure = constructor_failure_recorder(
            audit=self.audit,
            clock=self.clock,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            finalize=self._finalize_report,
            record_event=_record_pipeline_audit_event,
        )

        return await self._execute_prepared_run(
            context=context,
            run_logger=run_logger,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            started_monotonic=started_monotonic,
            record_constructor_failure=record_constructor_failure,
        )

    async def _execute_prepared_run(
        self,
        *,
        context: PipelineRunContext,
        run_logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
        started_at: datetime,
        started_monotonic: float,
        record_constructor_failure: Callable[[Exception], Awaitable[None]],
    ) -> RunResult:
        observation_token = bind_run_observations()
        accounting = StageAccountingAccumulator()
        accounting_token = bind_stage_accounting(accounting)
        try:
            runner = await create_execution_runner_audited(
                lambda: _require_execution_runner(self.runner_factory.create(context)),
                record_failure=record_constructor_failure,
            )
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
        except asyncio.CancelledError:
            self._finalize_report(
                RunResult(
                    status=PipelineRunResult.SHUTDOWN,
                    pipeline_name=pipeline_name,
                    run_id=str(run_id),
                    run_type=options.run_type,
                    started_at=started_at,
                    completed_at=self.clock.now(),
                    error_type="CancelledError",
                ),
                options,
            )
            raise
        finally:
            reset_stage_accounting(accounting_token)
            reset_run_observations(observation_token)

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
        result = build_pipeline_run_result(
            outcome=outcome,
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
            options=options,
            write_report=False,
            store=self.report_store,
        )
        return self._finalize_report(result, options)

    def _finalize_report(
        self, result: RunResult, options: RunOptions | None
    ) -> RunResult:
        """Capture control-plane evidence and persist the run report."""
        capture_run_completion(self.capture_control_plane, result, options)
        return finalize_pipeline_run_report(
            result=result,
            options=options,
            report_root=self.report_root,
            store=self.report_store,
        )
