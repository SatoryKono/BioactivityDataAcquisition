"""Pipeline runner service for universal pipeline execution.

Provides a high-level, interface-agnostic API for running pipelines.
Can be used from CLI, REST API, Airflow operators, or any other orchestrator.

Implements RULES.md §1.1 - Application Layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from bioetl.domain.context import (
    InputFilterContext,
    PipelineRunContext,
    VacuumConfig,
)
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsExtractorPort,
        RunnablePort,
        RunnerFactoryPort,
    )


class RunStatus(str, Enum):
    """Pipeline run completion status.

    Attributes:
        SUCCESS: Pipeline completed successfully.
        SHUTDOWN: Pipeline was gracefully shut down (SIGTERM/SIGINT).
        FAILED: Pipeline failed with an error.
        DRY_RUN: Dry-run mode, no actual execution performed.
    """

    SUCCESS = "success"
    SHUTDOWN = "shutdown"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class RunResult:
    """Result of pipeline execution.

    Provides execution metrics and status for orchestration layers.
    This is the unified return type for PipelineRunnerService.run()
    and enables programmatic access to execution results.

    Attributes:
        status: Completion status (success, shutdown, failed, dry_run).
        pipeline_name: Name of the executed pipeline.
        run_id: Unique identifier for this run.
        run_type: Type of run (incremental, backfill, rebuild).
        records_fetched: Total records retrieved from source.
        records_bronze: Records written to Bronze layer.
        records_silver: Records written to Silver layer.
        records_gold: Records written to Gold layer.
        records_quarantined: Records sent to quarantine.
        started_at: Timestamp when execution started.
        completed_at: Timestamp when execution completed.
        error_message: Error message if status is FAILED.
        error_type: Exception class name if status is FAILED.

    Example:
        >>> result = await service.run("chembl_activity")
        >>> if result.status == RunStatus.SUCCESS:
        ...     print(f"Processed {result.records_silver} records")
        >>> elif result.status == RunStatus.FAILED:
        ...     print(f"Failed: {result.error_message}")
    """

    status: RunStatus
    pipeline_name: str
    run_id: str
    run_type: str
    records_fetched: int = 0
    records_bronze: int = 0
    records_silver: int = 0
    records_gold: int = 0
    records_quarantined: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    error_message: str | None = None
    error_type: str | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate (non-quarantined / fetched)."""
        if self.records_fetched == 0:
            return 1.0
        return (self.records_fetched - self.records_quarantined) / self.records_fetched

    @property
    def is_success(self) -> bool:
        """Check if run was successful (or dry_run)."""
        return self.status in (RunStatus.SUCCESS, RunStatus.DRY_RUN)


@dataclass(frozen=True)
class RunOptions:
    """Options for running a pipeline.

    These are the user-facing options that can be set via CLI, REST API,
    or any other orchestration interface.

    Attributes:
        run_type: Type of run (incremental, backfill, rebuild). Default: incremental.
        resume: Whether to resume from the last checkpoint.
        limit: Maximum number of records to process.
        dry_run: Preview mode without execution.
        input_csv: Path to CSV file with filter IDs.
        filter_column: Column name in CSV containing filter IDs.
        filter_field: API field name to filter by.
        vacuum_after_run: Enable automatic VACUUM after successful run.
        vacuum_retention_days: Minimum age of files to remove during VACUUM.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.
    """

    run_type: str = "incremental"
    resume: bool = False
    limit: int | None = None
    dry_run: bool = False
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None
    log_level: str = "INFO"


class PipelineNotFoundError(ValueError):
    """Raised when a pipeline is not found in the registry."""

    def __init__(self, pipeline_name: str, available: list[str]) -> None:
        self.pipeline_name = pipeline_name
        self.available = available
        super().__init__(
            f"Unknown pipeline: {pipeline_name}. Available: {available}"
        )


@dataclass
class PipelineRunnerService:
    """Application service for running pipelines.

    Provides a universal, interface-agnostic API for pipeline execution.
    Stateless and thread-safe - creates runners per call via injected factory.

    This service can be used from:
    - CLI (Click/Typer commands)
    - REST API (FastAPI/Flask endpoints)
    - Schedulers (Airflow operators, Prefect flows)
    - Python scripts (direct programmatic access)

    Attributes:
        runner_factory: Factory for creating pipeline runners (injected).
        metrics_extractor: Extractor for runner execution metrics (injected).
        logger: Structured logger for observability (injected).

    Example:
        >>> service = get_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
        >>> print(f"Processed {result.records_silver} records in {result.duration_seconds}s")
    """

    runner_factory: RunnerFactoryPort
    metrics_extractor: MetricsExtractorPort
    logger: LoggerPort

    async def run(
        self,
        pipeline_name: str,
        config_path: Path | None = None,
        overrides: dict[str, Any] | None = None,
        dry_run: bool = False,
        run_id: UUID | None = None,
        options: RunOptions | None = None,
    ) -> RunResult:
        """Run a pipeline with the given configuration.

        This is the main entry point for pipeline execution. It handles:
        - Pipeline validation and resolution
        - Configuration loading and merging
        - Run ID creation
        - Dry-run preview mode
        - Exception classification and result building

        Args:
            pipeline_name: Name of the pipeline to run (e.g., 'chembl_activity').
            config_path: Optional path to config file (not implemented yet).
            overrides: Optional config overrides as dict (not implemented yet).
            dry_run: If True, only preview what would be done.
            run_id: Optional run ID. If None, a new UUID is generated.
            options: Optional RunOptions for detailed configuration.
                     If provided, takes precedence over individual parameters.

        Returns:
            RunResult with execution metrics and status.

        Raises:
            PipelineNotFoundError: If pipeline_name is not registered.

        Example:
            >>> result = await service.run("chembl_activity", dry_run=True)
            >>> if result.status == RunStatus.DRY_RUN:
            ...     print("Would process pipeline chembl_activity")
        """
        started_at = datetime.now(tz=UTC)

        # Merge options with individual parameters
        effective_options = self._merge_options(options, dry_run)

        # Validate pipeline exists
        if not self.runner_factory.contains(pipeline_name):
            available = self.runner_factory.list_pipelines()
            raise PipelineNotFoundError(pipeline_name, available)

        # Generate run_id if not provided
        effective_run_id: RunID = cast(RunID, run_id or uuid4())

        self.logger.info(
            "Starting pipeline run",
            pipeline=pipeline_name,
            run_id=str(effective_run_id),
            run_type=effective_options.run_type,
            dry_run=effective_options.dry_run,
            limit=effective_options.limit,
        )

        # Handle dry-run mode
        if effective_options.dry_run:
            self.logger.info(
                "Dry-run mode: no execution performed",
                pipeline=pipeline_name,
                run_id=str(effective_run_id),
            )
            return RunResult(
                status=RunStatus.DRY_RUN,
                pipeline_name=pipeline_name,
                run_id=str(effective_run_id),
                run_type=effective_options.run_type,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC),
            )

        # Build context and create runner
        context = self._build_context(pipeline_name, effective_run_id, effective_options)
        runner = self.runner_factory.create(context)

        # Execute pipeline
        return await self._execute_pipeline(
            runner=runner,
            pipeline_name=pipeline_name,
            run_id=effective_run_id,
            run_type=effective_options.run_type,
            started_at=started_at,
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
        """Merge individual parameters with RunOptions.

        Args:
            options: Optional RunOptions object.
            dry_run: Dry-run flag (fallback if options not provided).

        Returns:
            RunOptions with merged values.
        """
        if options is not None:
            return options

        return RunOptions(dry_run=dry_run)

    def _build_context(
        self,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
    ) -> PipelineRunContext:
        """Build PipelineRunContext from options.

        Args:
            pipeline_name: Name of the pipeline.
            run_id: Unique run identifier.
            options: Run options.

        Returns:
            PipelineRunContext ready for runner creation.
        """
        # Build InputFilterContext
        if options.input_csv:
            input_filter = InputFilterContext(
                enabled=True,
                source_path=options.input_csv,
                column_name=options.filter_column or "",
                filter_field=options.filter_field or "",
            )
        else:
            input_filter = InputFilterContext.disabled()

        # Build VacuumConfig
        vacuum = VacuumConfig(
            enabled=options.vacuum_after_run,
            retention_days=options.vacuum_retention_days or 7,
        )

        return PipelineRunContext(
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=RunType(options.run_type),
            resume=options.resume,
            limit=options.limit,
            dry_run=options.dry_run,
            input_filter=input_filter,
            vacuum=vacuum,
            log_level=options.log_level,
        )

    async def _execute_pipeline(
        self,
        runner: RunnablePort,
        pipeline_name: str,
        run_id: RunID,
        run_type: str,
        started_at: datetime,
    ) -> RunResult:
        """Execute pipeline and build result.

        Args:
            runner: Pipeline runner to execute.
            pipeline_name: Name of the pipeline.
            run_id: Run identifier.
            run_type: Type of run.
            started_at: Execution start time.

        Returns:
            RunResult with execution outcome.
        """
        # Import inside method to avoid circular import:
        # application/services/__init__.py -> pipeline_runner_service.py
        # -> application/core/shutdown.py -> application/services/shutdown_service.py
        from bioetl.application.core.shutdown import PipelineShutdownError

        status = RunStatus.SUCCESS
        error_message: str | None = None
        error_type: str | None = None

        try:
            await runner.run()
            self.logger.info(
                "Pipeline completed successfully",
                pipeline=pipeline_name,
                run_id=str(run_id),
            )
        except PipelineShutdownError:
            status = RunStatus.SHUTDOWN
            self.logger.warning(
                "Pipeline was gracefully shut down",
                pipeline=pipeline_name,
                run_id=str(run_id),
            )
        except Exception as e:
            status = RunStatus.FAILED
            error_message = str(e)
            error_type = type(e).__name__
            self.logger.exception(
                "Pipeline failed with exception",
                pipeline=pipeline_name,
                run_id=str(run_id),
                error_type=error_type,
            )

        completed_at = datetime.now(tz=UTC)

        # Extract metrics from runner
        metrics = self.metrics_extractor.extract_metrics(runner)

        return RunResult(
            status=status,
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            run_type=run_type,
            records_fetched=metrics.get("records_fetched", 0),
            records_bronze=metrics.get("records_bronze", 0),
            records_silver=metrics.get("records_silver", 0),
            records_gold=metrics.get("records_gold", 0),
            records_quarantined=metrics.get("records_quarantined", 0),
            started_at=started_at,
            completed_at=completed_at,
            error_message=error_message,
            error_type=error_type,
        )
