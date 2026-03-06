"""Policy helpers for run command error handling and control flow."""

from __future__ import annotations

from typing import NoReturn, Protocol

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
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
]


class RunExecutorCallable(Protocol):
    """Callable contract for synchronous pipeline execution from CLI."""

    def __call__(
        self,
        pipeline: str,
        options: RunOptions,
        health_server: bool,
        health_port: int,
    ) -> RunResult: ...


class ResultPresenterCallable(Protocol):
    """Callable contract to render run result output."""

    def __call__(self, result: RunResult) -> None: ...


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


def handle_cli_failure(
    exc: BaseException,
    *,
    pipeline: str,
    reason_code: str,
) -> None:
    """Handle CLI failures with consistent reason_code semantics."""
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
    """Map pipeline status and error type to CLI exit code."""
    return map_run_status_to_exit_code(status, error_type)


def handle_destructive_step(
    *,
    pipeline: str,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Run destructive confirmation/preview step with CLI error policy."""
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
    except Exception as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
        )
        return False


def execute_run_step(
    *,
    pipeline: str,
    options: RunOptions,
    health_server: bool,
    health_port: int,
    execute_run: RunExecutorCallable,
) -> RunResult:
    """Run pipeline execution step with CLI failure mapping."""
    try:
        return execute_run(
            pipeline=pipeline,
            options=options,
            health_server=health_server,
            health_port=health_port,
        )
    except PipelineNotFoundError as exc:
        handle_cli_failure(exc, pipeline=pipeline, reason_code="CLI_RUN_CONFIG_ERROR")
    except BioETLError as exc:
        handle_cli_failure(exc, pipeline=pipeline, reason_code="CLI_RUN_DOMAIN_ERROR")
    except KeyboardInterrupt as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_RUN_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_RUN_UNEXPECTED_ERROR",
        )
    raise RuntimeError("unreachable: handle_cli_failure is expected to terminate")


def finalize_run_step(
    *,
    result: RunResult,
    result_presenter: ResultPresenterCallable,
    exit_func: ExitCallable,
) -> None:
    """Render result and terminate process with mapped exit code."""
    exit_code = map_status_to_exit_code(result.status, result.error_type)
    result_presenter(result)
    exit_func(exit_code)
