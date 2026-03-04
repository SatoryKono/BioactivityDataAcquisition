"""Run-all command for executing all pipelines for a specific provider.

Provides a universal command to run all pipelines for a given source (provider),
replacing the need for hardcoded provider-specific commands.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.composition.registry import get_default_registry
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
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


def _get_available_providers() -> list[str]:
    """Get sorted list of unique provider names from registered pipelines."""
    registry = get_default_registry()
    pipelines = registry.list_pipelines()
    providers = {p.split("_")[0] for p in pipelines if "_" in p}
    return sorted(providers)


def _filter_pipelines_by_provider(provider: str) -> list[str]:
    """Filter registered pipelines by provider prefix."""
    registry = get_default_registry()
    all_pipelines = registry.list_pipelines()
    return sorted([name for name in all_pipelines if name.startswith(f"{provider}_")])


def _validate_provider(provider: str) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines."""
    available_providers = _get_available_providers()
    if not available_providers:
        return False, "No pipelines are registered."
    pipelines = _filter_pipelines_by_provider(provider)
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
            batch_result.results.append(result)

            if result.status == PipelineRunResult.SUCCESS:
                batch_result.succeeded += 1
                echo_info(f"[OK] {pipeline}: completed successfully")
            elif result.status == PipelineRunResult.DRY_RUN:
                batch_result.skipped += 1
                echo_info(f"[DRY] {pipeline}: dry-run (no changes)")
            elif result.status == PipelineRunResult.SHUTDOWN:
                batch_result.skipped += 1
                echo_warning(f"[STOP] {pipeline}: gracefully shut down")
                # Stop processing remaining pipelines on shutdown
                break
            elif result.status == PipelineRunResult.FAILED:
                batch_result.failed += 1
                batch_result.failed_pipelines.append(pipeline)
                echo_error(
                    f"[FAIL] {pipeline}: failed",
                    result.error_message or "Unknown error",
                )
        except PipelineNotFoundError as e:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(f"[FAIL] {pipeline}: not found", str(e))
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(
                f"[FAIL] {pipeline}: unexpected error",
                (
                    f"{exc} "
                    f"(reason_code=CLI_RUN_ALL_PIPELINE_ERROR, pipeline={pipeline}, "
                    f"error_type={type(exc).__name__})"
                ),
            )

    return batch_result


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server."""
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(enabled=health_server_enabled, port=health_port):
        service = get_pipeline_runner_service()
        return await _run_pipelines_batch(service, pipelines, options)


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary."""
    echo_info("")
    echo_info("=" * 50)

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
    """Show what pipelines will be run."""
    if dry_run:
        echo_info(f"[DRY-RUN] Would run {len(pipelines)} pipeline(s) for '{source}':")
    else:
        echo_info(f"Running {len(pipelines)} pipeline(s) for '{source}':")

    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")


def _determine_exit_code(batch_result: BatchRunResult) -> ExitCode:
    """Determine exit code from batch result."""
    if batch_result.all_succeeded:
        return ExitCode.OK
    if batch_result.failed > 0:
        return ExitCode.PIPELINE_ERROR
    # All skipped (shutdown)
    return ExitCode.SIGINT


@click.command("run-all")
@click.option(
    "--source",
    required=True,
    help="Provider name (e.g., chembl, pubchem, uniprot)",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run for all pipelines",
)
@click.option("--limit", type=int, help="Maximum records per pipeline")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview mode - show pipelines without execution",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt for rebuild/backfill",
)
@click.option(
    "--list-only",
    is_flag=True,
    help="List pipelines for the source without running them",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable DEBUG level logging",
)
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
    """Run all ETL pipelines for a specific provider.

    Executes all registered pipelines matching the given source (provider).
    Pipelines are run sequentially in alphabetical order.

    Examples:

        bioetl run-all --source chembl

        bioetl run-all --source chembl --list-only

        bioetl run-all --source pubchem --dry-run

        bioetl run-all --source chembl --run-type rebuild --yes

    Args:
        source: Data source.
        run_type: Type of pipeline run.
        limit: Maximum number of records to process.
        dry_run: Dry run mode flag.
        yes: Whether to yes.
        list_only: Whether to list only.
        debug: Whether to debug.
        health_server: Whether to health server.
        health_port: Health port.
    """
    # Validate provider has pipelines
    is_valid, error_msg = _validate_provider(source)
    if not is_valid:
        echo_error("Provider error", error_msg)
        sys.exit(ExitCode.FAIL)

    # Get pipelines for provider
    pipelines = _filter_pipelines_by_provider(source)

    # Handle --list-only mode
    if list_only:
        _handle_list_only(source, pipelines)

    # Handle confirmation for destructive operations (CLI responsibility)
    _handle_destructive_confirmation(run_type, pipelines, dry_run, yes)

    # Show what we're about to do
    _show_run_preview(source, pipelines, dry_run)

    # Display health server info
    echo_health_server_info(health_server, health_port)

    # Build options and run pipelines
    options = RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )

    coro = _run_all_pipelines_async(
        pipelines,
        options,
        health_server_enabled=health_server,
        health_port=health_port,
    )
    try:
        batch_result = asyncio.run(coro)
    except BioETLError as exc:
        echo_error(
            "Batch execution failed with domain error",
            (
                f"{exc} "
                f"(reason_code=CLI_RUN_ALL_DOMAIN_ERROR, source={source}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        sys.exit(ExitCode.FAIL)
    except KeyboardInterrupt:
        echo_warning("Batch run interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as exc:
        echo_error(
            "Unexpected error during batch execution",
            (
                f"{exc} "
                f"(reason_code=CLI_RUN_ALL_UNEXPECTED_ERROR, source={source}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        sys.exit(ExitCode.FAIL)
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

    # Output summary and exit
    _echo_batch_summary(batch_result, dry_run)
    sys.exit(_determine_exit_code(batch_result))


__all__ = [
    "BatchRunResult",
    "run_all",
]
