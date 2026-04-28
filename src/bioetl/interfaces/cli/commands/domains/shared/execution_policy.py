"""Shared CLI execution policy for orchestration commands.

Centralizes command-level error handling and exit-code mapping for:
- run
- run-all
- run-composite
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.exit_codes import ExitCode, get_exit_code_for_exception
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

__all__ = [
    "CLI_ENTRYPOINT_TYPED_ERRORS",
    "BatchRunResultProtocol",
    "ExecutionFailureReasonCodes",
    "build_failure_context",
    "execute_prepared_cli_flow",
    "execute_with_cli_failure_policy",
    "finalize_cli_execution",
    "handle_cli_failure",
    "map_batch_run_result_to_exit_code",
    "map_run_status_to_exit_code",
    "map_success_flag_to_exit_code",
    "render_failure_context",
]

_ResultT = TypeVar("_ResultT")

CLI_ENTRYPOINT_TYPED_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    TimeoutError,
)

_FAILED_STATUS_EXIT_OVERRIDES: Mapping[str, ExitCode] = {
    "ValueError": ExitCode.CONFIG_ERROR,
    "FileNotFoundError": ExitCode.EX_NOINPUT,
    "ConfigValidationError": ExitCode.CONFIG_ERROR,
    "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
    "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
    "LockAcquisitionError": ExitCode.LOCK_ERROR,
    "LockLostError": ExitCode.LOCK_ERROR,
    "StorageError": ExitCode.STORAGE_ERROR,
    "NetworkError": ExitCode.NETWORK_ERROR,
    "RateLimitError": ExitCode.NETWORK_ERROR,
    "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
}


class BatchRunResultProtocol(Protocol):
    """Protocol for batch run result objects used in exit-code mapping."""

    @property
    def failed(self) -> int:
        """Return the number of failed runs."""
        ...

    @property
    def total(self) -> int:
        """Return the total number of runs."""
        ...

    @property
    def results(self) -> Sequence[object]:
        """Return the individual run results."""
        ...


class CliFailureHandler(Protocol):
    """Callable contract for structured CLI failure handling."""

    def __call__(
        self,
        exc: BaseException,
        subject: str,
        reason_code: str,
    ) -> None:
        """Handle one exception for one logical command subject."""
        ...


@dataclass(frozen=True, slots=True)
class ExecutionFailureReasonCodes:
    """Reason-code bundle for typed CLI exception handling."""

    config: str
    domain: str
    interrupted: str
    unexpected: str


def map_run_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map single pipeline status to CLI exit code.

    Args:
        status: PipelineRunResult enum value (SUCCESS, DRY_RUN, SHUTDOWN, or FAILED).
        error_type: Exception class name from the failed run; used to select a
            specific exit code when status is FAILED. None for non-failure statuses.

    Returns:
        ExitCode corresponding to the pipeline run status and error type.
    """
    if status in (PipelineRunResult.SUCCESS, PipelineRunResult.DRY_RUN):
        return ExitCode.OK
    if status == PipelineRunResult.SHUTDOWN:
        return ExitCode.SIGINT
    if error_type is not None:
        return _FAILED_STATUS_EXIT_OVERRIDES.get(error_type, ExitCode.PIPELINE_ERROR)
    return ExitCode.PIPELINE_ERROR


def map_batch_run_result_to_exit_code(batch_result: BatchRunResultProtocol) -> ExitCode:
    """Map batched pipeline result to CLI exit code.

    Args:
        batch_result: BatchRunResultProtocol with failed count, total count, and
            individual run result objects.

    Returns:
        ExitCode based on the number of failures and shutdown signals in the batch.
    """
    if batch_result.failed > 0:
        return ExitCode.PIPELINE_ERROR
    if any(
        getattr(result, "status", None) == PipelineRunResult.SHUTDOWN
        for result in batch_result.results
    ):
        return ExitCode.SIGINT
    if batch_result.total > 0:
        return ExitCode.OK
    return ExitCode.SIGINT


def map_success_flag_to_exit_code(
    success: bool,
    *,
    failure_exit_code: ExitCode = ExitCode.PIPELINE_ERROR,
) -> ExitCode:
    """Map boolean command outcome to CLI exit code.

    Args:
        success: When True, returns ExitCode.OK; when False, returns failure_exit_code.
        failure_exit_code: Exit code to return on failure; defaults to
            ExitCode.PIPELINE_ERROR.

    Returns:
        ExitCode.OK if success is True, otherwise the specified failure_exit_code.
    """
    if success:
        return ExitCode.OK
    return failure_exit_code


def execute_with_cli_failure_policy[ResultT](
    action: Callable[[], _ResultT],
    *,
    subject: str,
    reason_codes: ExecutionFailureReasonCodes,
    failure_handler: CliFailureHandler,
) -> _ResultT | None:
    """Execute one command action with the canonical typed-failure ladder."""
    try:
        return action()
    except PipelineNotFoundError as exc:
        failure_handler(exc, subject, reason_codes.config)
    except BioETLError as exc:
        failure_handler(exc, subject, reason_codes.domain)
    except KeyboardInterrupt as exc:
        failure_handler(exc, subject, reason_codes.interrupted)
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        failure_handler(exc, subject, reason_codes.unexpected)
    return None


def finalize_cli_execution[ResultT](
    *,
    health_info_presenter: Callable[[], None],
    execute: Callable[[], _ResultT | None],
    result_finalizer: Callable[[_ResultT], None],
) -> None:
    """Run the prepared health -> execute -> finalize command shell."""
    health_info_presenter()
    result = execute()
    if result is None:
        return
    result_finalizer(result)


def execute_prepared_cli_flow[ResultT](
    *,
    health_info_presenter: Callable[[], None],
    execute: Callable[[], _ResultT | None],
    result_finalizer: Callable[[_ResultT], None],
) -> None:
    """Execute one prepared CLI flow using the shared execution shell."""
    finalize_cli_execution(
        health_info_presenter=health_info_presenter,
        execute=execute,
        result_finalizer=result_finalizer,
    )


def build_failure_context(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> dict[str, object]:
    """Build structured context for CLI failure diagnostics.

    Args:
        exc: Exception to build context from; BioETLError instances use their
            own structured context method.
        reason_code: Machine-readable code attached to error context (e.g.,
            'CLI_RUN_DOMAIN_ERROR').
        subject_key: Key name for the structured context field (e.g., 'pipeline').
        subject_value: Value for the structured context field (e.g., 'chembl_activity').

    Returns:
        Dictionary with structured error context including message, reason_code,
        subject key/value, and error type.
    """
    if isinstance(exc, BioETLError):
        structured_context: dict[str, object] = exc.to_structured_context(
            reason_code=reason_code,
            **{subject_key: subject_value},
        )
        return structured_context

    return {
        "message": str(exc),
        "reason_code": reason_code,
        subject_key: subject_value,
        "error_type": type(exc).__name__,
    }


def render_failure_context(context: Mapping[str, object]) -> str:
    """Render a structured failure context as stable human-readable text.

    Args:
        context: Structured failure context mapping with at least a 'message' key
            and optional metadata fields.

    Returns:
        Human-readable string combining the message and sorted metadata fields.
    """
    message = str(context.get("message", ""))
    keys = [key for key in context if key != "message"]
    keys.sort()
    metadata = ", ".join(f"{key}={context[key]}" for key in keys)
    if not metadata:
        return message
    if not message:
        return metadata
    return f"{message} ({metadata})"


def _format_failure_detail(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> str:
    failure_context = build_failure_context(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
    )
    return render_failure_context(failure_context)


def handle_cli_failure(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
    default_exit_code: ExitCode = ExitCode.FAIL,
) -> None:
    """Handle command-level exceptions with a consistent policy.

    Maps the exception type to the appropriate exit code, formats a structured
    error message, echoes it to stderr, and calls sys.exit() with the mapped code.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code attached to error context (e.g.,
            'CLI_COMPOSITE_DOMAIN_ERROR').
        subject_key: Key name for the structured context field (e.g., 'pipeline').
        subject_value: Value for the structured context field (e.g., 'chembl_activity').
        domain_error_title: Title shown for BioETLError exceptions.
        unexpected_error_title: Title shown for non-domain exceptions.
        interrupted_message: Message shown when KeyboardInterrupt is caught.
        default_exit_code: Fallback exit code when no specific code is determined.
            Defaults to ExitCode.FAIL.
    """
    if isinstance(exc, PipelineNotFoundError):
        echo_error("Pipeline not found", str(exc))
        sys.exit(ExitCode.CONFIG_ERROR)

    if isinstance(exc, KeyboardInterrupt):
        echo_warning(interrupted_message)
        sys.exit(ExitCode.SIGINT)

    detail = _format_failure_detail(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
    )

    if isinstance(exc, BioETLError):
        domain_exit = get_exit_code_for_exception(exc)
        if domain_exit == ExitCode.FAIL:
            domain_exit = default_exit_code
        echo_error(domain_error_title, detail)
        sys.exit(domain_exit)

    exit_code = get_exit_code_for_exception(exc)
    if exit_code == ExitCode.FAIL:
        exit_code = default_exit_code
    echo_error(unexpected_error_title, detail)
    sys.exit(exit_code)
