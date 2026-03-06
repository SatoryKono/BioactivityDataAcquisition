"""Application-level orchestration for CLI run command execution."""

from __future__ import annotations

__all__ = [
    "CliRunOrchestrationService",
    "MetricsFlushCallable",
    "RunCoroutineCallable",
    "RunPipelineAsyncCallable",
    "StartOffsetValidationResult",
]


from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any, Protocol

from bioetl.application.services.pipeline_runner_service import RunOptions, RunResult


class RunPipelineAsyncCallable(Protocol):
    """Callable contract for async pipeline execution."""

    def __call__(
        self,
        pipeline: str,
        options: RunOptions,
        *,
        health_server_enabled: bool = True,
        health_port: int,
    ) -> Coroutine[Any, Any, RunResult]: ...  # Any: standard Coroutine type params


class RunCoroutineCallable(Protocol):
    """Callable contract to execute awaitables in sync context."""

    def __call__(
        self,
        main: Coroutine[Any, Any, RunResult],  # Any: standard Coroutine type params
        *,
        debug: bool | None = None,
    ) -> RunResult: ...


class MetricsFlushCallable(Protocol):
    """Callable contract for metrics flush at command boundary."""

    def __call__(
        self,
        job: str = "bioetl",
        pipeline_name: str | None = None,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class StartOffsetValidationResult:
    """Validation result for start-offset related CLI options."""

    is_valid: bool
    error_message: str | None = None


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

    def execute_pipeline(
        self,
        *,
        pipeline: str,
        options: RunOptions,
        health_server: bool,
        health_port: int,
        run_pipeline_async: RunPipelineAsyncCallable,
        run_coroutine: RunCoroutineCallable,
        flush_metrics: MetricsFlushCallable,
    ) -> RunResult:
        """Execute pipeline with deterministic metrics flush.

        Returns:
            RunResult from the completed pipeline execution.
        """
        coro = run_pipeline_async(
            pipeline,
            options,
            health_server_enabled=health_server,
            health_port=health_port,
        )
        try:
            return run_coroutine(coro)
        finally:
            flush_metrics(pipeline_name=pipeline)
            if getattr(coro, "cr_frame", None) is not None:
                coro.close()
