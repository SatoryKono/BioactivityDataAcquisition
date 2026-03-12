"""Policy helpers for run command error handling and control flow."""

from __future__ import annotations

from typing import NoReturn, Protocol

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService,
    RunExecutionRequest,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    map_run_status_to_exit_code,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.run_helpers import (
    handle_destructive_run_confirmation,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "execute_run_step",
    "finalize_run_step",
    "handle_cli_failure",
    "handle_destructive_step",
    "map_status_to_exit_code",
    "prepare_run_request",
]


class RunExecutorCallable(Protocol):
    """Callable contract for synchronous pipeline execution from CLI."""

    def __call__(self, request: RunExecutionRequest) -> RunResult: ...


class ResultPresenterCallable(Protocol):
    """Callable contract to render run result output."""

    def __call__(self, result: RunResult) -> None: ...


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


def prepare_run_request(
    *,
    service: CliRunOrchestrationService,
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
    exit_func: ExitCallable,
) -> RunExecutionRequest:
    """Validate raw CLI inputs and build the prepared request for execution."""
    preparation = service.prepare_execution_request(
        pipeline=pipeline,
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
        health_server=health_server,
        health_port=health_port,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
    )
    if preparation.request is not None:
        return preparation.request
    if preparation.error_message is not None:
        echo_error(preparation.error_message)
    exit_func(ExitCode.CONFIG_ERROR)
    raise RuntimeError("unreachable: exit_func is expected to terminate")


def handle_cli_failure(
    exc: BaseException,
    *,
    pipeline: str,
    reason_code: str,
) -> None:
    """Handle CLI failures with consistent reason_code semantics.

    Routes cleanup-preview errors to a simplified formatter and delegates all
    other exceptions to the shared execution_policy handler which calls sys.exit.

    Args:
        exc: Exception caught at the CLI command boundary.
        pipeline: Pipeline name for structured error context.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_RUN_DOMAIN_ERROR').
    """
    if reason_code.startswith("CLI_CLEANUP_PREVIEW"):
        echo_error(
            "Error previewing cleanup",
            (
                f"{exc} "
                f"(reason_code={reason_code}, pipeline={pipeline}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        return

    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title="Pipeline execution failed with domain error",
        unexpected_error_title="Unexpected error during pipeline execution",
        interrupted_message="Pipeline interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def map_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map pipeline status and error type to CLI exit code.

    Args:
        status: PipelineRunResult enum value (SUCCESS, FAILED, SHUTDOWN, DRY_RUN).
        error_type: Exception class name from the failed run; used to select a
            specific exit code when status is FAILED. None for non-failure statuses.

    Returns:
        ExitCode corresponding to the pipeline run status and optional error type.
    """
    return map_run_status_to_exit_code(status, error_type)


def handle_destructive_step(
    *,
    pipeline: str,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Run destructive confirmation/preview step with CLI error policy.

    Args:
        pipeline: Pipeline name for confirmation messages and error context.
        run_type: Type of run (e.g., 'rebuild', 'backfill'); only those types trigger
            the confirmation/preview flow.
        dry_run: When True, shows a cleanup preview and returns False without running.
        yes: When True, skips the interactive confirmation prompt.

    Returns:
        True if pipeline execution should continue, False if cancelled or dry-run
        preview was shown.
    """
    try:
        return handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes)
    except click.Abort:
        raise
    except BioETLError as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
        )
        return False
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
        )
        return False


def execute_run_step(
    *,
    request: RunExecutionRequest,
    execute_run: RunExecutorCallable,
) -> RunResult:
    """Run pipeline execution step with CLI failure mapping.

    Delegates to the provided executor and maps all exception types to
    structured CLI failure handling (which calls sys.exit on failure).

    Args:
        request: Prepared CLI run request.
        execute_run: Callable that synchronously runs the pipeline and returns RunResult.

    Returns:
        RunResult with pipeline execution status and metrics.
    """
    try:
        return execute_run(request)
    except PipelineNotFoundError as exc:
        handle_cli_failure(
            exc,
            pipeline=request.pipeline,
            reason_code="CLI_RUN_CONFIG_ERROR",
        )
    except BioETLError as exc:
        handle_cli_failure(
            exc,
            pipeline=request.pipeline,
            reason_code="CLI_RUN_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        handle_cli_failure(
            exc,
            pipeline=request.pipeline,
            reason_code="CLI_RUN_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handle_cli_failure(
            exc,
            pipeline=request.pipeline,
            reason_code="CLI_RUN_UNEXPECTED_ERROR",
        )
    raise RuntimeError("unreachable: handle_cli_failure is expected to terminate")


def finalize_run_step(
    *,
    result: RunResult,
    result_presenter: ResultPresenterCallable,
    exit_func: ExitCallable,
) -> None:
    """Render result and terminate process with mapped exit code.

    Args:
        result: RunResult from the completed pipeline execution.
        result_presenter: Callable that formats and prints the result to the terminal.
        exit_func: Callable that terminates the process with the given exit code.
    """
    exit_code = map_status_to_exit_code(result.status, result.error_type)
    result_presenter(result)
    exit_func(exit_code)
