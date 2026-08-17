"""Policy helpers for run command error handling and control flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn, Protocol

import click

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.run.support import (
    handle_destructive_run_confirmation,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    ExecutionFailureReasonCodes,
    execute_prepared_cli_flow,
    execute_with_cli_failure_policy,
    map_run_status_to_exit_code,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        RunExecutionRequest,
    )
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

__all__ = [
    "RunCommandInput",
    "execute_run_step",
    "finalize_run_step",
    "handle_cli_failure",
    "handle_destructive_step",
    "map_status_to_exit_code",
    "prepare_run_request",
    "run_command_flow",
]


class RunExecutorCallable(Protocol):
    """Callable contract for synchronous pipeline execution from CLI."""

    def __call__(self, request: RunExecutionRequest) -> RunResult: ...


class ResultPresenterCallable(Protocol):
    """Callable contract to render run result output."""

    def __call__(self, result: RunResult) -> None: ...


class ResultFinalizerCallable(Protocol):
    """Callable contract to present a run result and terminate accordingly."""

    def __call__(self, result: RunResult) -> None: ...


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


class HealthInfoPresenterCallable(Protocol):
    """Callable contract to render health-server info for a prepared request."""

    def __call__(self, request: RunExecutionRequest) -> None: ...


@dataclass(frozen=True, slots=True)
class RunCommandInput:
    """Normalized CLI inputs for the run command control flow."""

    pipeline: str
    run_type: str
    resume: bool
    start_offset: int | None
    limit: int | None
    input_csv: str | None
    filter_column: str | None
    filter_field: str | None
    dry_run: bool
    yes: bool
    vacuum_after_run: bool | None
    vacuum_retention_days: int | None
    debug: bool
    health_server: bool
    health_port: int
    enable_tracing: bool | None
    use_cached_bronze: bool
    cached_bronze_date: str | None
    cached_bronze_path: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    resume_run_id: str | None = None
    resume_manifest_id: str | None = None
    exact_replay: bool = False
    required_persistence_profile: str | None = None
    ensure_observability_backend: bool = False
    observability_backend_port: int = 8000


def prepare_run_request(
    *,
    service: CliRunOrchestrationService,
    command_input: RunCommandInput,
    exit_func: ExitCallable,
) -> RunExecutionRequest:
    """Validate raw CLI inputs and build the prepared request for execution."""
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        CliRunOptionsInput,
        CliRunPreparationInput,
    )

    preparation = service.prepare_execution_request(
        CliRunPreparationInput(
            pipeline=command_input.pipeline,
            options=CliRunOptionsInput(
                run_type=command_input.run_type,
                resume=command_input.resume,
                start_offset=command_input.start_offset,
                limit=command_input.limit,
                input_csv=command_input.input_csv,
                filter_column=command_input.filter_column,
                filter_field=command_input.filter_field,
                dry_run=command_input.dry_run,
                vacuum_after_run=command_input.vacuum_after_run,
                vacuum_retention_days=command_input.vacuum_retention_days,
                debug=command_input.debug,
                enable_tracing=command_input.enable_tracing,
                use_cached_bronze=command_input.use_cached_bronze,
                cached_bronze_date=command_input.cached_bronze_date,
                cached_bronze_path=command_input.cached_bronze_path,
                replay_of_run_id=command_input.replay_of_run_id,
                replay_of_manifest_id=command_input.replay_of_manifest_id,
                resume_run_id=command_input.resume_run_id,
                resume_manifest_id=command_input.resume_manifest_id,
                exact_replay=command_input.exact_replay,
                required_persistence_profile=(
                    command_input.required_persistence_profile
                ),
            ),
            health_server=command_input.health_server,
            health_port=command_input.health_port,
        )
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
        raise SystemExit(ExitCode.FAIL) from exc

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


def run_command_flow(
    *,
    cli_input: RunCommandInput,
    service: CliRunOrchestrationService,
    execute_run: RunExecutorCallable,
    health_info_presenter: HealthInfoPresenterCallable,
    result_finalizer: ResultFinalizerCallable,
    exit_func: ExitCallable,
) -> None:
    """Execute the full run-command policy flow from normalized CLI input."""
    if not handle_destructive_step(
        pipeline=cli_input.pipeline,
        run_type=cli_input.run_type,
        dry_run=cli_input.dry_run,
        yes=cli_input.yes,
    ):
        return

    request = prepare_run_request(
        service=service,
        command_input=cli_input,
        exit_func=exit_func,
    )
    execute_prepared_cli_flow(
        health_info_presenter=lambda: health_info_presenter(request),
        execute=lambda: execute_run_step(
            request=request,
            execute_run=execute_run,
        ),
        result_finalizer=result_finalizer,
    )


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
    result = execute_with_cli_failure_policy(
        lambda: execute_run(request),
        subject=request.pipeline,
        reason_codes=ExecutionFailureReasonCodes(
            config="CLI_RUN_CONFIG_ERROR",
            domain="CLI_RUN_DOMAIN_ERROR",
            interrupted="CLI_RUN_SIGINT",
            unexpected="CLI_RUN_UNEXPECTED_ERROR",
        ),
        failure_handler=lambda exc, subject, reason_code: handle_cli_failure(
            exc,
            pipeline=subject,
            reason_code=reason_code,
        ),
    )
    if result is not None:
        return result
    raise RuntimeError("unreachable: handle_cli_failure is expected to terminate")


def finalize_run_step(
    *,
    run_result: RunResult,
    result_finalizer: ResultFinalizerCallable,
) -> None:
    """Finalize CLI execution for a completed run result.

    Args:
        run_result: RunResult from the completed pipeline execution.
        result_finalizer: Callable that renders the result and terminates the CLI.
    """
    result_finalizer(run_result)
