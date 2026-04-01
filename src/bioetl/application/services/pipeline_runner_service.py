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


from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from bioetl.application.services.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.pipeline_run_execution_service import (
    PipelineExecutionResult,
    PipelineRunExecutionService,
)
from bioetl.application.services.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        ClockPort,
        ExecutionMetricsRunnerPort,
        LoggerPort,
        MetricsExtractorPort,
        RunnerFactoryPort,
    )


@dataclass
class PipelineRunnerService:
    """Application service for running pipelines.

    Provides a universal, interface-agnostic API for pipeline execution.
    Stateless and thread-safe - creates runners per call via injected factory.

    This service can be used from:
    - CLI (Click commands)
    - REST API (FastAPI/Flask endpoints)
    - Schedulers (Airflow operators, Prefect flows)
    - Python scripts (direct programmatic access)

    Attributes:
        runner_factory: Factory for creating pipeline runners (injected).
        metrics_extractor: Extractor for runner execution metrics (injected).
        logger: Structured logger for observability (injected).
        _context_service: Helper service for building effective options and run context.
        _execution_service: Helper service for executing the prepared runner.

    Example:
        >>> service = get_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
        >>> logger.info("pipeline_complete", records_silver=result.records_silver, duration_s=result.duration_seconds)
    """

    runner_factory: RunnerFactoryPort
    metrics_extractor: MetricsExtractorPort
    logger: LoggerPort
    clock: ClockPort
    _context_service: PipelineRunContextService
    _execution_service: PipelineRunExecutionService

    @staticmethod
    def _require_execution_runner(
        runner: object,
    ) -> ExecutionMetricsRunnerPort:
        """Validate producer output before pipeline side effects begin."""
        from bioetl.domain.ports import ExecutionMetricsRunnerPort

        if not isinstance(runner, ExecutionMetricsRunnerPort):
            raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
        return runner

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
            run_id: Optional explicit UUID for the run. Auto-generated if None.
            options: Optional RunOptions controlling run type, limit, filters, etc.
                If None, a default RunOptions instance is created using dry_run.

        Returns:
            RunResult with status, record counts, duration, and error details.

        Raises:
            PipelineNotFoundError: If pipeline_name is not registered in the factory.
        """
        started_at = self.clock.now()
        effective_options = self._merge_options(options, dry_run)
        self._ensure_pipeline_exists(pipeline_name)
        effective_run_id: RunID = cast(RunID, run_id or uuid4())
        context = self._build_context(
            pipeline_name, effective_run_id, effective_options
        )
        run_logger = self._create_run_logger(
            context=context,
            options=effective_options,
        )
        dry_run_result = self._maybe_dry_run_result(
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            options=effective_options,
            started_at=started_at,
            run_logger=run_logger,
        )
        if dry_run_result is not None:
            return dry_run_result

        runner = self._require_execution_runner(self.runner_factory.create(context))
        return await self._execute_pipeline(
            runner=runner,
            run_logger=run_logger,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            run_type=effective_options.run_type,
            started_at=started_at,
        )

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
        if not options.dry_run:
            return None
        run_logger.info("Dry-run mode: no execution performed")
        return RunResult(
            status=PipelineRunResult.DRY_RUN,
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            run_type=options.run_type,
            started_at=started_at,
            completed_at=self.clock.now(),
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
    ) -> PipelineRunContext:
        """Build PipelineRunContext from options."""
        return self._context_service.build_context(
            pipeline_name=pipeline_name,
            run_id=run_id,
            options=options,
        )

    async def _execute_pipeline(
        self,
        runner: ExecutionMetricsRunnerPort,
        run_logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
    ) -> RunResult:
        """Execute pipeline and build normalized RunResult."""
        outcome = await self._execution_service.execute(
            runner=runner,
            run_logger=run_logger,
            metrics_extractor=self.metrics_extractor,
        )
        return self._build_run_result(
            outcome=outcome,
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=run_type,
            started_at=started_at,
        )

    def _build_run_result(
        self,
        *,
        outcome: PipelineExecutionResult,
        runner: ExecutionMetricsRunnerPort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
    ) -> RunResult:
        """Convert execution outcome to public RunResult contract."""
        status = PipelineRunResult(outcome.status)
        metrics = outcome.metrics
        return RunResult(
            status=status,
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            manifest_id=getattr(runner, "manifest_id", None),
            run_type=run_type,
            records_fetched=metrics.get("records_fetched", 0),
            records_bronze=metrics.get("records_bronze", 0),
            records_silver=metrics.get("records_silver", 0),
            records_gold=metrics.get("records_gold", 0),
            records_quarantined=metrics.get("records_quarantined", 0),
            records_filtered_out=metrics.get("records_filtered_out", 0),
            started_at=started_at,
            completed_at=outcome.completed_at,
            error_message=outcome.error_message,
            error_type=outcome.error_type,
        )
