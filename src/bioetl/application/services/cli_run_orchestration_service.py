"""Application-level orchestration for CLI run command execution."""

from __future__ import annotations

__all__ = [
    "CliRunOrchestrationService",
    "MetricsFlushCallable",
    "RunCoroutineCallable",
    "RunExecutionRequest",
    "RunPreparationResult",
    "RunPreparedPipelineCallable",
    "StartOffsetValidationResult",
]


from bioetl.application.services.cli_run_orchestration_contracts import (
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunPreparedPipelineCallable,
)
from bioetl.application.services.cli_run_orchestration_models import (
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)
from bioetl.application.services.pipeline_runner_service import RunOptions, RunResult


class CliRunOrchestrationService:
    """Coordinates run-option preparation and execution mechanics for CLI."""

    def validate_start_offset(
        self,
        *,
        start_offset: int | None,
        run_type: str,
        resume: bool,
    ) -> StartOffsetValidationResult:
        """Validate start offset constraints for run command options.

        Args:
            start_offset: Optional record offset to start processing from.
                Must be non-negative and only valid for incremental runs.
            run_type: Pipeline run type string (e.g. 'incremental', 'backfill').
            resume: Whether the run resumes a previously interrupted pipeline.
                Mutually exclusive with start_offset.

        Returns:
            StartOffsetValidationResult with is_valid flag and optional error_message.
        """
        if start_offset is None:
            return StartOffsetValidationResult(is_valid=True)
        if start_offset < 0:
            return StartOffsetValidationResult(
                is_valid=False,
                error_message="--start-offset must be non-negative",
            )
        if run_type != "incremental":
            return StartOffsetValidationResult(
                is_valid=False,
                error_message="--start-offset requires --run-type=incremental",
            )
        if resume:
            return StartOffsetValidationResult(
                is_valid=False,
                error_message="--start-offset and --resume cannot be used together",
            )
        return StartOffsetValidationResult(is_valid=True)

    def build_options(
        self,
        *,
        run_type: str,
        resume: bool,
        start_offset: int | None,
        limit: int | None,
        input_csv: str | None,
        filter_column: str | None,
        filter_field: str | None,
        dry_run: bool,
        vacuum_after_run: bool | None,
        vacuum_retention_days: int | None,
        debug: bool,
        use_cached_bronze: bool,
        cached_bronze_date: str | None,
        cached_bronze_path: str | None,
    ) -> RunOptions:
        """Build RunOptions from CLI input.

        Args:
            run_type: Pipeline run type ('incremental', 'backfill', 'rebuild').
            resume: Whether to resume from a previously interrupted run.
            start_offset: Optional record offset for incremental runs.
            limit: Optional maximum number of records to process.
            input_csv: Optional path to CSV file with input IDs.
            filter_column: Optional column name to apply ID filtering.
            filter_field: Optional field name for API-side filtering.
            dry_run: If True, validate and plan but do not write to storage.
            vacuum_after_run: If True, vacuum Delta tables after the run.
            vacuum_retention_days: Number of days for Delta vacuum retention.
            debug: If True, sets log level to DEBUG.
            use_cached_bronze: If True, use a previously cached Bronze extract.
            cached_bronze_date: Date string for the cached Bronze snapshot.
            cached_bronze_path: File system path to the cached Bronze snapshot.

        Returns:
            RunOptions populated from the provided CLI parameters.
        """
        return RunOptions(
            run_type=run_type,
            resume=resume,
            start_offset=start_offset,
            limit=limit,
            dry_run=dry_run,
            input_csv=input_csv,
            filter_column=filter_column,
            filter_field=filter_field,
            vacuum_after_run=vacuum_after_run if vacuum_after_run else None,
            vacuum_retention_days=vacuum_retention_days,
            log_level="DEBUG" if debug else "INFO",
            use_cached_bronze=use_cached_bronze,
            cached_bronze_path=cached_bronze_path,
            cached_bronze_date=cached_bronze_date,
        )

    def prepare_execution_request(
        self,
        *,
        pipeline: str,
        run_type: str,
        resume: bool,
        start_offset: int | None,
        limit: int | None,
        input_csv: str | None,
        filter_column: str | None,
        filter_field: str | None,
        dry_run: bool,
        vacuum_after_run: bool | None,
        vacuum_retention_days: int | None,
        debug: bool,
        health_server: bool,
        health_port: int,
        use_cached_bronze: bool,
        cached_bronze_date: str | None,
        cached_bronze_path: str | None,
    ) -> RunPreparationResult:
        """Validate raw CLI inputs and build a prepared execution request."""
        validation = self.validate_start_offset(
            start_offset=start_offset,
            run_type=run_type,
            resume=resume,
        )
        if not validation.is_valid:
            return RunPreparationResult(error_message=validation.error_message)

        return RunPreparationResult(
            request=RunExecutionRequest(
                pipeline=pipeline,
                options=self.build_options(
                    run_type=run_type,
                    resume=resume,
                    start_offset=start_offset,
                    limit=limit,
                    input_csv=input_csv,
                    filter_column=filter_column,
                    filter_field=filter_field,
                    dry_run=dry_run,
                    vacuum_after_run=vacuum_after_run,
                    vacuum_retention_days=vacuum_retention_days,
                    debug=debug,
                    use_cached_bronze=use_cached_bronze,
                    cached_bronze_date=cached_bronze_date,
                    cached_bronze_path=cached_bronze_path,
                ),
                health_server=health_server,
                health_port=health_port,
            )
        )

    def execute_pipeline(
        self,
        *,
        request: RunExecutionRequest,
        run_pipeline_async: RunPreparedPipelineCallable,
        run_coroutine: RunCoroutineCallable,
        flush_metrics: MetricsFlushCallable,
    ) -> RunResult:
        """Execute pipeline with deterministic metrics flush.

        Args:
            request: Prepared run request with execution options and health settings.
            run_pipeline_async: Callable that creates the async pipeline coroutine.
            run_coroutine: Callable that runs the coroutine in a sync context.
            flush_metrics: Callable to flush metrics after the pipeline finishes.

        Returns:
            RunResult from the completed pipeline execution.
        """
        coro = run_pipeline_async(request)
        try:
            return run_coroutine(coro)
        finally:
            flush_metrics(pipeline_name=request.pipeline)
            if getattr(coro, "cr_frame", None) is not None:
                coro.close()
