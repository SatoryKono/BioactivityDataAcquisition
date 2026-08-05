"""Policy helpers for run-all command control flow."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import NoReturn, Protocol

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    PipelineRegistryView,
    RunAllExecutionPlan,
    resolve_run_all_execution_plan,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    execute_prepared_cli_flow,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "RunAllCommandInput",
    "build_run_all_command_input",
    "exit_with_code",
    "finalize_batch_step",
    "handle_run_all_cli_failure",
    "prepare_run_all_execution_plan",
    "run_all_command_flow",
]


class ExitCallable(Protocol):
    """Callable contract for terminating with a process exit code."""

    def __call__(self, code: int | str | None = None) -> NoReturn: ...


class ListingEmitterCallable(Protocol):
    """Callable contract for list-only run-all output."""

    def __call__(self, *, source: str, pipelines: list[str]) -> None: ...


class PreviewEmitterCallable(Protocol):
    """Callable contract for pre-execution run-all preview output."""

    def __call__(self, *, source: str, pipelines: list[str], dry_run: bool) -> None: ...


class DestructiveConfirmationCallable(Protocol):
    """Callable contract for destructive-run confirmation flow."""

    def __call__(
        self,
        run_type: str,
        pipelines: list[str],
        dry_run: bool,
        yes: bool,
    ) -> bool: ...


class HealthInfoPresenterCallable(Protocol):
    """Callable contract for health-server presentation."""

    def __call__(self, enabled: bool, port: int) -> None: ...


class BatchExecutorCallable(Protocol):
    """Callable contract for synchronous run-all batch execution."""

    def __call__(
        self,
        *,
        source: str,
        pipelines: list[str],
        options: RunOptions,
        health_server: bool,
        health_port: int,
        registry: PipelineRegistry | None = None,
    ) -> BatchRunResult | None: ...


class BatchSummaryPresenterCallable(Protocol):
    """Callable contract for rendering the completed batch summary."""

    def __call__(self, result: BatchRunResult, dry_run: bool) -> None: ...


class BatchExitCodeCallable(Protocol):
    """Callable contract for mapping a batch result to the final exit code."""

    def __call__(self, result: BatchRunResult) -> ExitCode: ...


@dataclass(frozen=True, slots=True)
class RunAllCommandInput:
    """Normalized CLI inputs for the run-all command control flow."""

    source: str
    run_type: str
    limit: int | None
    dry_run: bool
    yes: bool
    list_only: bool
    debug: bool
    health_server: bool
    health_port: int
    ensure_observability_backend: bool = False
    observability_backend_port: int = 8000


def exit_with_code(code: int | str | None = None) -> NoReturn:
    """Typed wrapper around sys.exit for policy-flow injection."""
    sys.exit(code)


def build_run_all_command_input(
    *,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
    ensure_observability_backend: bool = False,
    observability_backend_port: int = 8000,
) -> RunAllCommandInput:
    """Build normalized CLI input payload for run_all_command_flow."""
    return RunAllCommandInput(
        source=source,
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        yes=yes,
        list_only=list_only,
        debug=debug,
        health_server=health_server,
        health_port=health_port,
        ensure_observability_backend=ensure_observability_backend,
        observability_backend_port=observability_backend_port,
    )


def handle_run_all_cli_failure(
    exc: BaseException,
    *,
    source: str,
    reason_code: str,
) -> None:
    """Handle run-all CLI failures with consistent reason_code semantics."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="source",
        subject_value=source,
        domain_error_title="Batch execution failed with domain error",
        unexpected_error_title="Unexpected error during batch execution",
        interrupted_message="Batch run interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def prepare_run_all_execution_plan(
    *,
    cli_input: RunAllCommandInput,
    registry: PipelineRegistryView | None = None,
    exit_func: ExitCallable,
) -> RunAllExecutionPlan:
    """Validate run-all inputs and build the prepared execution plan."""
    execution_plan, error_msg = resolve_run_all_execution_plan(
        source=cli_input.source,
        run_type=cli_input.run_type,
        limit=cli_input.limit,
        dry_run=cli_input.dry_run,
        debug=cli_input.debug,
        registry=registry,
    )
    if execution_plan is not None:
        return execution_plan
    if error_msg is not None:
        echo_error("Provider error", error_msg)
    exit_func(ExitCode.FAIL)
    raise RuntimeError("unreachable: exit_func is expected to terminate")


def finalize_batch_step(
    *,
    batch_result: BatchRunResult,
    dry_run: bool,
    summary_presenter: BatchSummaryPresenterCallable,
    determine_exit_code: BatchExitCodeCallable,
    exit_func: ExitCallable,
) -> None:
    """Present the completed batch result and terminate with its exit code."""
    summary_presenter(batch_result, dry_run)
    exit_func(determine_exit_code(batch_result))


def run_all_command_flow(
    *,
    cli_input: RunAllCommandInput,
    registry: PipelineRegistry | None,
    destructive_confirmation: DestructiveConfirmationCallable,
    listing_emitter: ListingEmitterCallable,
    preview_emitter: PreviewEmitterCallable,
    health_info_presenter: HealthInfoPresenterCallable,
    execute_batch: BatchExecutorCallable,
    summary_presenter: BatchSummaryPresenterCallable,
    determine_exit_code: BatchExitCodeCallable,
    exit_func: ExitCallable,
) -> None:
    """Execute the full run-all control flow from normalized CLI input."""
    execution_plan = prepare_run_all_execution_plan(
        cli_input=cli_input,
        registry=registry,
        exit_func=exit_func,
    )
    pipelines = execution_plan.pipelines

    if cli_input.list_only:
        listing_emitter(source=cli_input.source, pipelines=pipelines)
        exit_func(ExitCode.OK)

    destructive_confirmation(
        cli_input.run_type,
        pipelines,
        cli_input.dry_run,
        cli_input.yes,
    )
    preview_emitter(
        source=cli_input.source,
        pipelines=pipelines,
        dry_run=cli_input.dry_run,
    )
    execute_prepared_cli_flow(
        health_info_presenter=lambda: health_info_presenter(
            cli_input.health_server,
            cli_input.health_port,
        ),
        execute=lambda: execute_batch(
            source=cli_input.source,
            pipelines=pipelines,
            options=execution_plan.options,
            health_server=cli_input.health_server,
            health_port=cli_input.health_port,
            registry=registry,
        ),
        result_finalizer=lambda batch_result: finalize_batch_step(
            batch_result=batch_result,
            dry_run=cli_input.dry_run,
            summary_presenter=summary_presenter,
            determine_exit_code=determine_exit_code,
            exit_func=exit_func,
        ),
    )
