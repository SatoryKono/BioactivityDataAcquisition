"""Run-all CLI command."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    RunOptions,
    RunResult,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    map_batch_run_result_to_exit_code,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    create_run_all_options,
    record_pipeline_failure,
    record_pipeline_result,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunnerService


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


def _get_available_providers(
    registry: PipelineRegistry | None = None,
) -> list[str]:
    """Get sorted list of unique provider names from registered pipelines."""
    reg = registry if registry is not None else get_default_registry()
    pipelines = reg.list_pipelines()
    providers = {p.split("_")[0] for p in pipelines if "_" in p}
    return sorted(providers)


def _filter_pipelines_by_provider(
    provider: str,
    registry: PipelineRegistry | None = None,
) -> list[str]:
    """Filter registered pipelines by provider prefix."""
    reg = registry if registry is not None else get_default_registry()
    all_pipelines = reg.list_pipelines()
    return sorted([name for name in all_pipelines if name.startswith(f"{provider}_")])


def _validate_provider(
    provider: str,
    registry: PipelineRegistry | None = None,
) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines."""
    available_providers = _get_available_providers(registry=registry)
    if not available_providers:
        return False, "No pipelines are registered."
    pipelines = _filter_pipelines_by_provider(provider, registry=registry)
    if not pipelines:
        return False, (
            f"No pipelines found for provider '{provider}'. "
            f"Available providers: {', '.join(available_providers)}"
        )
    return True, None


async def _run_pipeline_async(
    service: PipelineRunnerService, pipeline: str, options: RunOptions
) -> RunResult:
    """Run a single pipeline asynchronously."""
    return await service.run(pipeline, options=options)


async def _run_pipelines_batch(
    service: PipelineRunnerService, pipelines: list[str], options: RunOptions
) -> BatchRunResult:
    """Run pipelines sequentially within a service context."""
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            result = await _run_pipeline_async(service, pipeline, options)
            if record_pipeline_result(
                batch_result=batch_result,
                pipeline=pipeline,
                result=result,
            ):
                break  # Stop processing remaining pipelines on shutdown
        except PipelineNotFoundError as e:
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: not found",
                detail=str(e),
            )
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            error_msg = (
                f"{exc} (reason_code=CLI_RUN_ALL_PIPELINE_ERROR, "
                f"pipeline={pipeline}, error_type={type(exc).__name__})"
            )
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: unexpected error",
                detail=error_msg,
            )

    return batch_result


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server.

    Args:
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server_enabled: When True, starts the HTTP health server before
            pipeline execution. Defaults to True.
        health_port: TCP port the health server listens on. Defaults to
            DEFAULT_HEALTH_SERVER_PORT.

    Returns:
        BatchRunResult aggregating results from all pipeline runs.
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(enabled=health_server_enabled, port=health_port):
        service = get_pipeline_runner_service()
        return await _run_pipelines_batch(service, pipelines, options)


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary.

    Args:
        result: BatchRunResult with aggregate counts for the completed batch.
        dry_run: When True, prints a dry-run preview summary instead of execution stats.
    """
    echo_info("\n" + "=" * 50)
    if dry_run:
        echo_info(f"Dry-run complete: {result.total} pipelines previewed")
    else:
        echo_info(f"Batch run complete: {result.total} pipelines")
        echo_info(f"  Succeeded: {result.succeeded}")
        if result.failed > 0:
            echo_info(f"  Failed: {result.failed}")
        if result.skipped > 0:
            echo_info(f"  Skipped: {result.skipped}")
    if result.failed_pipelines:
        echo_error("Failed pipelines:", ", ".join(result.failed_pipelines))


def _handle_list_only(source: str, pipelines: list[str]) -> None:
    """Handle --list-only mode and exit."""
    echo_info(f"Pipelines for provider '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info(f"\nTotal: {len(pipelines)} pipeline(s)")
    sys.exit(ExitCode.OK)


def _handle_destructive_confirmation(
    run_type: str, pipelines: list[str], dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for destructive operations.

    Args:
        run_type: Type of run; only 'rebuild' and 'backfill' trigger the confirmation
            prompt.
        pipelines: List of pipeline names that will be affected by the operation.
        dry_run: When True, skips the confirmation prompt.
        yes: When True, bypasses the interactive confirmation prompt.

    Returns:
        True if should continue, False if cancelled.
    """
    if run_type not in ("rebuild", "backfill") or dry_run or yes:
        return True

    echo_warning(f"{run_type} will clear existing data for {len(pipelines)} pipelines.")
    echo_info("Pipelines to be affected:")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")

    if not click.confirm("\nDo you want to continue?"):
        echo_info("Operation cancelled.")
        sys.exit(ExitCode.OK)
    return True


def _show_run_preview(source: str, pipelines: list[str], dry_run: bool) -> None:
    """Show what pipelines will be run.

    Args:
        source: Provider name shown in the preview header.
        pipelines: List of pipeline names that will be (or would be) executed.
        dry_run: When True, prefixes the output with a dry-run indicator.
    """
    prefix = "[DRY-RUN] Would run" if dry_run else "Running"
    echo_info(f"{prefix} {len(pipelines)} pipeline(s) for '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")


def _determine_exit_code(batch_result: BatchRunResult) -> ExitCode:
    """Determine exit code from batch result."""
    return map_batch_run_result_to_exit_code(batch_result)


def _handle_run_all_failure(
    exc: BaseException, *, source: str, reason_code: str
) -> None:
    """Handle run-all CLI failures with consistent error policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        source: Provider name used as subject value in the structured error context.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_RUN_ALL_DOMAIN_ERROR').
    """
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


def _run_batch_with_policy(
    *,
    source: str,
    pipelines: list[str],
    options: RunOptions,
    health_server: bool,
    health_port: int,
) -> BatchRunResult | None:
    """Execute async batch run with typed exception policy.

    Args:
        source: Provider name used in error context for structured failure handling.
        pipelines: Ordered list of pipeline names to run sequentially.
        options: RunOptions controlling run type, limits, and filter settings.
        health_server: When True, enables the HTTP health server during execution.
        health_port: TCP port the health server listens on.

    Returns:
        BatchRunResult on success, None if an exception was handled and process will exit.
    """
    coro = _run_all_pipelines_async(
        pipelines, options, health_server_enabled=health_server, health_port=health_port
    )
    try:
        return asyncio.run(coro)
    except PipelineNotFoundError as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_CONFIG_ERROR"
        )
    except BioETLError as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_DOMAIN_ERROR"
        )
    except KeyboardInterrupt as exc:
        _handle_run_all_failure(exc, source=source, reason_code="CLI_RUN_ALL_SIGINT")
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_run_all_failure(
            exc, source=source, reason_code="CLI_RUN_ALL_UNEXPECTED_ERROR"
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


@click.command("run-all")
@click.option(
    "--source", required=True, help="Provider name (e.g., chembl, pubchem, uniprot)"
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run for all pipelines",
)
@click.option("--limit", type=int, help="Maximum records per pipeline")
@click.option(
    "--dry-run", is_flag=True, help="Preview mode - show pipelines without execution"
)
@click.option(
    "--yes", "-y", is_flag=True, help="Skip confirmation prompt for rebuild/backfill"
)
@click.option(
    "--list-only",
    is_flag=True,
    help="List pipelines for the source without running them",
)
@click.option("--debug", is_flag=True, help="Enable DEBUG level logging")
@click.option(
    "--health-server/--no-health-server",
    "health_server",
    default=True,
    help="Enable/disable HTTP health server during execution.",
    show_default=True,
)
@click.option(
    "--health-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the HTTP health server.",
    show_default=True,
)
def run_all(
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Run all registered pipelines for one provider sequentially."""
    ctx = click.get_current_context()
    registry = ctx.obj if isinstance(ctx.obj, PipelineRegistry) else None
    is_valid, error_msg = _validate_provider(source, registry=registry)
    if not is_valid:
        echo_error("Provider error", error_msg)
        sys.exit(ExitCode.FAIL)

    pipelines = _filter_pipelines_by_provider(source, registry=registry)

    if list_only:
        _handle_list_only(source, pipelines)

    _handle_destructive_confirmation(run_type, pipelines, dry_run, yes)

    _show_run_preview(source, pipelines, dry_run)

    echo_health_server_info(health_server, health_port)

    options = create_run_all_options(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        debug=debug,
    )
    batch_result = _run_batch_with_policy(
        source=source,
        pipelines=pipelines,
        options=options,
        health_server=health_server,
        health_port=health_port,
    )
    if batch_result is None:
        return

    _echo_batch_summary(batch_result, dry_run)
    sys.exit(_determine_exit_code(batch_result))


__all__ = ["BatchRunResult", "run_all"]
