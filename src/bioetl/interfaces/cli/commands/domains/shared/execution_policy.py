"""Shared CLI execution policy for orchestration commands.

Centralizes command-level error handling and exit-code mapping for:
- run
- run-all
- run-composite
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared._execution_failure_support import (
    build_failure_context,
    handle_cli_failure,
    render_failure_context,
)
from bioetl.interfaces.cli.exit_codes import EXCEPTION_EXIT_CODES, ExitCode

__all__ = [
    "CLI_ENTRYPOINT_TYPED_ERRORS",
    "BatchRunResultProtocol",
    "CliBoundaryExecutionPolicy",
    "ExecutionFailureReasonCodes",
    "build_failure_context",
    "build_target_cli_boundary_policy",
    "execute_prepared_cli_flow",
    "execute_with_cli_failure_policy",
    "finalize_cli_execution",
    "handle_boundary_cli_failure",
    "handle_cli_failure",
    "map_batch_run_result_to_exit_code",
    "map_run_status_to_exit_code",
    "map_success_flag_to_exit_code",
    "render_failure_context",
    "run_async_with_cli_failure_policy",
    "run_sync_with_cli_failure_policy",
]

CLI_ENTRYPOINT_TYPED_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    TimeoutError,
)

_FAILED_STATUS_EXIT_OVERRIDE_NAMES = (
    "ValueError",
    "FileNotFoundError",
    "ConfigValidationError",
    "DataQualityError",
    "DataQualityThresholdError",
    "LockAcquisitionError",
    "LockLostError",
    "StorageError",
    "NetworkError",
    "RateLimitError",
    "CircuitBreakerOpenError",
)
_FAILED_STATUS_EXIT_OVERRIDES: Mapping[str, ExitCode] = {
    name: EXCEPTION_EXIT_CODES[name] for name in _FAILED_STATUS_EXIT_OVERRIDE_NAMES
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


@dataclass(frozen=True, slots=True)
class CliBoundaryExecutionPolicy:
    """Typed policy for one CLI command boundary."""

    reason_prefix: str
    subject_key: str
    subject_value: str
    domain_error_title: str
    unexpected_error_title: str
    interrupted_message: str
    default_exit_code: ExitCode = ExitCode.FAIL


def build_target_cli_boundary_policy(
    *,
    reason_prefix: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
    default_exit_code: ExitCode = ExitCode.FAIL,
) -> CliBoundaryExecutionPolicy:
    """Build the canonical target-scoped CLI boundary policy."""
    return CliBoundaryExecutionPolicy(
        reason_prefix=reason_prefix,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=default_exit_code,
    )


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
    return ExitCode.OK


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
    action: Callable[[], ResultT],
    *,
    subject: str,
    reason_codes: ExecutionFailureReasonCodes,
    failure_handler: CliFailureHandler,
) -> ResultT | None:
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
    execute: Callable[[], ResultT | None],
    result_finalizer: Callable[[ResultT], None],
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
    execute: Callable[[], ResultT | None],
    result_finalizer: Callable[[ResultT], None],
) -> None:
    """Execute one prepared CLI flow using the shared execution shell."""
    finalize_cli_execution(
        health_info_presenter=health_info_presenter,
        execute=execute,
        result_finalizer=result_finalizer,
    )


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


def _handle_boundary_failure(
    exc: BaseException,
    *,
    policy: CliBoundaryExecutionPolicy,
    reason_suffix: str,
) -> None:
    """Handle one exception using the shared CLI boundary policy."""
    handle_cli_failure(
        exc,
        reason_code=f"{policy.reason_prefix}_{reason_suffix}",
        subject_key=policy.subject_key,
        subject_value=policy.subject_value,
        domain_error_title=policy.domain_error_title,
        unexpected_error_title=policy.unexpected_error_title,
        interrupted_message=policy.interrupted_message,
        default_exit_code=policy.default_exit_code,
    )


def handle_boundary_cli_failure(
    exc: BaseException,
    *,
    policy: CliBoundaryExecutionPolicy,
    reason_suffix: str,
) -> None:
    """Handle one exception using a prepared command-boundary policy."""
    _handle_boundary_failure(
        exc,
        policy=policy,
        reason_suffix=reason_suffix,
    )


def _execute_boundary_action[ResultT](
    action: Callable[[], ResultT],
    *,
    policy: CliBoundaryExecutionPolicy,
    passthrough_exception_types: tuple[type[BaseException], ...] = (),
) -> ResultT | None:
    """Execute one command-boundary action with the shared typed-failure ladder."""
    try:
        return action()
    except BaseException as exc:
        if passthrough_exception_types and isinstance(exc, passthrough_exception_types):
            raise
        if isinstance(exc, BioETLError):
            _handle_boundary_failure(
                exc,
                policy=policy,
                reason_suffix="DOMAIN_ERROR",
            )
            return None
        if isinstance(exc, KeyboardInterrupt):
            _handle_boundary_failure(
                exc,
                policy=policy,
                reason_suffix="SIGINT",
            )
            return None
        if isinstance(exc, CLI_ENTRYPOINT_TYPED_ERRORS):
            _handle_boundary_failure(
                exc,
                policy=policy,
                reason_suffix="UNEXPECTED_ERROR",
            )
            return None
        raise


def run_async_with_cli_failure_policy[ResultT](
    coro: Coroutine[object, object, ResultT],
    *,
    policy: CliBoundaryExecutionPolicy,
    passthrough_exception_types: tuple[type[BaseException], ...] = (),
) -> ResultT | None:
    """Run an async CLI coroutine with the canonical typed-failure ladder."""
    try:
        return _execute_boundary_action(
            lambda: asyncio.run(coro),
            policy=policy,
            passthrough_exception_types=passthrough_exception_types,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


def run_sync_with_cli_failure_policy[ResultT](
    fn: Callable[[], ResultT],
    *,
    policy: CliBoundaryExecutionPolicy,
    passthrough_exception_types: tuple[type[BaseException], ...] = (),
) -> ResultT | None:
    """Run a sync CLI callable with the canonical typed-failure ladder."""
    return _execute_boundary_action(
        fn,
        policy=policy,
        passthrough_exception_types=passthrough_exception_types,
    )
