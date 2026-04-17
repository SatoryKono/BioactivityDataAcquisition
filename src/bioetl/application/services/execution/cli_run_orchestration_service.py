"""Application-level orchestration for CLI run command execution.

`CliRunOrchestrationService` is the behavioral owner for CLI request validation,
request preparation, and prepared execution. Data models and callable
protocols live in sibling canonical modules and are re-exported here only for
compatibility with existing imports.
"""

from __future__ import annotations

__all__ = [
    "CliRunOptionsInput",
    "CliRunPreparationInput",
    "CliRunOrchestrationService",
    "MetricsFlushCallable",
    "RunCoroutineCallable",
    "RunExecutionRequest",
    "RunPreparationResult",
    "RunPreparedPipelineCallable",
    "StartOffsetValidationResult",
]


from bioetl.application.services.execution.cli_run_orchestration_contracts import (
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunPreparedPipelineCallable,
)
from bioetl.application.services.execution.cli_run_orchestration_models import (
    CliRunOptionsInput,
    CliRunPreparationInput,
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
)


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
        request: CliRunOptionsInput,
    ) -> RunOptions:
        """Build RunOptions from CLI input.

        Args:
            request: Normalized CLI option values.

        Returns:
            RunOptions populated from the provided CLI parameters.
        """
        return RunOptions(
            run_type=request.run_type,
            resume=request.resume,
            start_offset=request.start_offset,
            limit=request.limit,
            dry_run=request.dry_run,
            input_csv=request.input_csv,
            filter_column=request.filter_column,
            filter_field=request.filter_field,
            vacuum_after_run=(
                request.vacuum_after_run if request.vacuum_after_run else None
            ),
            vacuum_retention_days=request.vacuum_retention_days,
            log_level="DEBUG" if request.debug else "INFO",
            use_cached_bronze=request.use_cached_bronze,
            cached_bronze_path=request.cached_bronze_path,
            cached_bronze_date=request.cached_bronze_date,
            replay_of_run_id=request.replay_of_run_id,
            replay_of_manifest_id=request.replay_of_manifest_id,
            exact_replay=request.exact_replay,
            enable_tracing=request.enable_tracing,
        )

    def prepare_execution_request(
        self,
        request: CliRunPreparationInput,
    ) -> RunPreparationResult:
        """Validate raw CLI inputs and build a prepared execution request."""
        validation = self.validate_start_offset(
            start_offset=request.options.start_offset,
            run_type=request.options.run_type,
            resume=request.options.resume,
        )
        if not validation.is_valid:
            return RunPreparationResult(error_message=validation.error_message)
        if (
            request.options.replay_of_run_id is not None
            or request.options.replay_of_manifest_id is not None
        ) and not request.options.exact_replay:
            return RunPreparationResult(
                error_message=(
                    "--replay-of-run-id/--replay-of-manifest-id require --exact-replay"
                )
            )
        if request.options.exact_replay and not request.options.use_cached_bronze:
            return RunPreparationResult(
                error_message=(
                    "--exact-replay currently requires --use-cached-bronze with snapshot-backed Bronze inputs"
                )
            )

        return RunPreparationResult(
            request=RunExecutionRequest(
                pipeline=request.pipeline,
                options=self.build_options(request.options),
                health_server=request.health_server,
                health_port=request.health_port,
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
