"""Shared CLI execution policy for orchestration commands.

Centralizes command-level error handling and exit-code mapping for:
- run
- run-all
- run-composite
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import Protocol

from bioetl.application.services import PipelineNotFoundError, PipelineRunResult
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.exit_codes import ExitCode, get_exit_code_for_exception
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

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
    @property
    def failed(self) -> int: ...

    @property
    def total(self) -> int: ...

    @property
    def results(self) -> Sequence[object]: ...


def map_run_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map single pipeline status to CLI exit code."""
    if status in (PipelineRunResult.SUCCESS, PipelineRunResult.DRY_RUN):
        return ExitCode.OK
    if status == PipelineRunResult.SHUTDOWN:
        return ExitCode.SIGINT
    if error_type is not None:
        return _FAILED_STATUS_EXIT_OVERRIDES.get(error_type, ExitCode.PIPELINE_ERROR)
    return ExitCode.PIPELINE_ERROR


def map_batch_run_result_to_exit_code(batch_result: BatchRunResultProtocol) -> ExitCode:
    """Map batched pipeline result to CLI exit code."""
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
    """Map boolean command outcome to CLI exit code."""
    if success:
        return ExitCode.OK
    return failure_exit_code


def build_failure_context(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> dict[str, object]:
    """Build structured context for CLI failure diagnostics."""
    if isinstance(exc, BioETLError):
        return exc.to_structured_context(
            reason_code=reason_code,
            **{subject_key: subject_value},
        )

    return {
        "message": str(exc),
        "reason_code": reason_code,
        subject_key: subject_value,
        "error_type": type(exc).__name__,
    }


def render_failure_context(context: Mapping[str, object]) -> str:
    """Render a structured failure context as stable human-readable text."""
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
    """Handle command-level exceptions with a consistent policy."""
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
