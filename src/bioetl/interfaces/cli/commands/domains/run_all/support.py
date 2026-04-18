"""Internal helper functions for the run-all CLI command."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NoReturn, Protocol, cast

import click

from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    map_batch_run_result_to_exit_code,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = [
    "BatchRunResult",
    "RunAllExecutionPlan",
    "create_run_all_options",
    "determine_batch_exit_code",
    "echo_batch_summary",
    "emit_destructive_confirmation_preview",
    "emit_run_all_listing",
    "emit_run_all_preview",
    "filter_pipelines_by_provider",
    "get_available_providers",
    "handle_destructive_confirmation",
    "record_pipeline_failure",
    "record_pipeline_result",
    "resolve_run_all_execution_plan",
    "resolve_run_all_registry",
    "should_prompt_for_destructive_run",
    "validate_provider",
]


class _BatchRunAccumulator(Protocol):
    """Minimal mutable contract needed for run-all batch result updates."""

    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[RunResult]
    failed_pipelines: list[str]


@dataclass
class BatchRunResult:
    """Result of running multiple pipelines."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[RunResult] = field(default_factory=list)
    failed_pipelines: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        """Check if all pipelines succeeded."""
        return self.failed == 0 and self.total > 0


@dataclass(frozen=True, slots=True)
class RunAllExecutionPlan:
    """Resolved pipelines and RunOptions for one run-all invocation."""

    pipelines: list[str]
    options: RunOptions


class PipelineRegistryView(Protocol):
    """Minimal registry contract used by run-all helper functions."""

    def list_pipelines(self) -> list[str]:
        """Return all registered pipeline names visible to the CLI."""
        ...


def _list_registered_pipelines(
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Return registered pipeline names from the resolved registry view."""
    return resolve_run_all_registry(registry).list_pipelines()


def _record_success(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a successful pipeline run."""
    batch_result.succeeded += 1
    echo_info(f"[OK] {pipeline}: completed successfully")
    return False


def _record_dry_run(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a dry-run preview result."""
    batch_result.skipped += 1
    echo_info(f"[DRY] {pipeline}: dry-run (no changes)")
    return False


def _record_shutdown(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
) -> bool:
    """Record a graceful shutdown result and stop the batch."""
    batch_result.skipped += 1
    echo_warning(f"[STOP] {pipeline}: gracefully shut down")
    return True


def resolve_run_all_registry(
    registry: PipelineRegistryView | None = None,
) -> PipelineRegistryView:
    """Resolve the registry view for run-all helper functions."""
    if registry is not None:
        return registry

    ctx = click.get_current_context(silent=True)
    candidate = getattr(ctx, "obj", None) if ctx is not None else None
    if candidate is None or not hasattr(candidate, "list_pipelines"):
        raise RuntimeError("run-all helpers require an explicit PipelineRegistry")
    return cast(PipelineRegistryView, candidate)


def get_available_providers(
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Get sorted list of unique provider names from registered pipelines."""
    pipelines = _list_registered_pipelines(registry=registry)
    providers = {p.split("_")[0] for p in pipelines if "_" in p}
    return sorted(providers)


def filter_pipelines_by_provider(
    provider: str,
    registry: PipelineRegistryView | None = None,
) -> list[str]:
    """Filter registered pipelines by provider prefix."""
    all_pipelines = _list_registered_pipelines(registry=registry)
    return sorted([name for name in all_pipelines if name.startswith(f"{provider}_")])


def validate_provider(
    provider: str,
    registry: PipelineRegistryView | None = None,
) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines."""
    available_providers = get_available_providers(registry=registry)
    if not available_providers:
        return False, "No pipelines are registered."
    pipelines = filter_pipelines_by_provider(provider, registry=registry)
    if not pipelines:
        return False, (
            f"No pipelines found for provider '{provider}'. "
            f"Available providers: {', '.join(available_providers)}"
        )
    return True, None


def create_run_all_options(
    *,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    debug: bool,
) -> RunOptions:
    """Build canonical RunOptions for the run-all command."""
    return RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )


def resolve_run_all_execution_plan(
    *,
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    debug: bool,
    registry: PipelineRegistryView | None = None,
) -> tuple[RunAllExecutionPlan | None, str | None]:
    """Resolve validated provider pipelines and canonical RunOptions."""
    is_valid, error = validate_provider(source, registry=registry)
    if not is_valid:
        return None, error

    return (
        RunAllExecutionPlan(
            pipelines=filter_pipelines_by_provider(source, registry=registry),
            options=create_run_all_options(
                run_type=run_type,
                limit=limit,
                dry_run=dry_run,
                debug=debug,
            ),
        ),
        None,
    )


def emit_run_all_listing(*, source: str, pipelines: list[str]) -> None:
    """Emit list-only output for provider pipelines."""
    echo_info(f"Pipelines for provider '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info(f"\nTotal: {len(pipelines)} pipeline(s)")


def should_prompt_for_destructive_run(
    *,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Return whether the CLI should prompt before destructive execution."""
    return run_type in ("rebuild", "backfill") and not dry_run and not yes


def emit_destructive_confirmation_preview(
    *,
    run_type: str,
    pipelines: list[str],
) -> None:
    """Emit the confirmation preview shown before destructive operations."""
    echo_warning(f"{run_type} will clear existing data for {len(pipelines)} pipelines.")
    echo_info("Pipelines to be affected:")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")


def handle_destructive_confirmation(
    *,
    run_type: str,
    pipelines: list[str],
    dry_run: bool,
    yes: bool,
    confirm_fn: Callable[[str], bool] = click.confirm,
    info_printer: Callable[..., None] = echo_info,
    exit_func: Callable[[int | str | None], NoReturn] = sys.exit,
) -> bool:
    """Handle confirmation flow for destructive run-all operations."""
    should_continue = True
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return should_continue

    emit_destructive_confirmation_preview(
        run_type=run_type,
        pipelines=pipelines,
    )

    should_continue = confirm_fn("\nDo you want to continue?")
    if not should_continue:
        info_printer("Operation cancelled.")
        exit_func(ExitCode.OK)
    return should_continue


def emit_run_all_preview(
    *,
    source: str,
    pipelines: list[str],
    dry_run: bool,
) -> None:
    """Emit the preview shown before running provider pipelines."""
    prefix = "[DRY-RUN] Would run" if dry_run else "Running"
    echo_info(f"{prefix} {len(pipelines)} pipeline(s) for '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")


def record_pipeline_result(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    result: RunResult,
) -> bool:
    """Record one pipeline result and return whether the batch should stop."""
    batch_result.results.append(result)

    if result.status == PipelineRunResult.SUCCESS:
        return _record_success(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.DRY_RUN:
        return _record_dry_run(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.SHUTDOWN:
        return _record_shutdown(batch_result=batch_result, pipeline=pipeline)

    if result.status == PipelineRunResult.FAILED:
        record_pipeline_failure(
            batch_result=batch_result,
            pipeline=pipeline,
            title=f"[FAIL] {pipeline}: failed",
            detail=result.error_message or "Unknown error",
        )

    return False


def record_pipeline_failure(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    title: str,
    detail: str,
) -> None:
    """Record a failed pipeline and emit a consistent error message."""
    batch_result.failed += 1
    batch_result.failed_pipelines.append(pipeline)
    echo_error(title, detail)


def determine_batch_exit_code(result: _BatchRunAccumulator) -> ExitCode:
    """Determine the CLI exit code from aggregate batch state."""
    return map_batch_run_result_to_exit_code(result)


def echo_batch_summary(
    *,
    result: _BatchRunAccumulator,
    dry_run: bool,
    info_printer: Callable[..., None] = echo_info,
    error_printer: Callable[..., None] = echo_error,
) -> None:
    """Emit batch run summary using injected output sinks."""
    info_printer("\n" + "=" * 50)
    if dry_run:
        info_printer(f"Dry-run complete: {result.total} pipelines previewed")
    else:
        info_printer(f"Batch run complete: {result.total} pipelines")
        info_printer(f"  Succeeded: {result.succeeded}")
        if result.failed > 0:
            info_printer(f"  Failed: {result.failed}")
        if result.skipped > 0:
            info_printer(f"  Skipped: {result.skipped}")
    if result.failed_pipelines:
        error_printer("Failed pipelines:", ", ".join(result.failed_pipelines))
