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
    RunOptions,
    RunResult,
    RunStatus,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunnerService


@dataclass
class BatchRunResult:
    """Result of running multiple pipelines.

    Attributes:
        total: Total number of pipelines.
        succeeded: Number of successful runs.
        failed: Number of failed runs.
        skipped: Number of skipped runs (dry-run or shutdown).
        results: List of individual run results.
        failed_pipelines: Names of pipelines that failed.
    """

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
    """Get list of available providers from registered pipelines.

    Returns:
        Sorted list of unique provider names.
    """
    registry = get_default_registry()
    pipelines = registry.list_pipelines()
    providers = set()
    for pipeline in pipelines:
        if "_" in pipeline:
            provider = pipeline.split("_")[0]
            providers.add(provider)
    return sorted(providers)


def _filter_pipelines_by_provider(provider: str) -> list[str]:
    """Filter registered pipelines by provider prefix.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        List of pipeline names matching the provider.
    """
    registry = get_default_registry()
    all_pipelines = registry.list_pipelines()
    return sorted([
        name for name in all_pipelines
        if name.startswith(f"{provider}_")
    ])


def _validate_provider(provider: str) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines.

    Args:
        provider: Provider name to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
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
    service: PipelineRunnerService,
    pipeline: str,
    options: RunOptions,
) -> RunResult:
    """Run a single pipeline asynchronously.

    Args:
        service: Pipeline runner service.
        pipeline: Pipeline name.
        options: Run options.

    Returns:
        RunResult with execution status.
    """
    return await service.run(pipeline, options=options)


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
) -> BatchRunResult:
    """Run all pipelines sequentially.

    Args:
        pipelines: List of pipeline names to run.
        options: Run options.

    Returns:
        BatchRunResult with aggregated results.
    """
    service = get_pipeline_runner_service()
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            result = await _run_pipeline_async(service, pipeline, options)
            batch_result.results.append(result)

            if result.status == RunStatus.SUCCESS:
                batch_result.succeeded += 1
                echo_info(f"✓ {pipeline}: completed successfully")
            elif result.status == RunStatus.DRY_RUN:
                batch_result.skipped += 1
                echo_info(f"○ {pipeline}: dry-run (no changes)")
            elif result.status == RunStatus.SHUTDOWN:
                batch_result.skipped += 1
                echo_warning(f"⊘ {pipeline}: gracefully shut down")
                # Stop processing remaining pipelines on shutdown
                break
            elif result.status == RunStatus.FAILED:
                batch_result.failed += 1
                batch_result.failed_pipelines.append(pipeline)
                echo_error(
                    f"✗ {pipeline}: failed",
                    result.error_message or "Unknown error"
                )
        except PipelineNotFoundError as e:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(f"✗ {pipeline}: not found", str(e))
        except Exception as e:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(f"✗ {pipeline}: unexpected error", str(e))

    return batch_result


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary.

    Args:
        result: BatchRunResult with aggregated results.
        dry_run: Whether this was a dry run.
    """
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
def run_all(
    source: str,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    yes: bool,
    list_only: bool,
    debug: bool,
) -> None:
    """Run all ETL pipelines for a specific provider.

    Executes all registered pipelines matching the given source (provider).
    Pipelines are run sequentially in alphabetical order.

    Examples:

        bioetl run-all --source chembl

        bioetl run-all --source chembl --list-only

        bioetl run-all --source pubchem --dry-run

        bioetl run-all --source chembl --run-type rebuild --yes
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
        echo_info(f"Pipelines for provider '{source}':")
        for pipeline in pipelines:
            echo_info(f"  - {pipeline}")
        echo_info(f"\nTotal: {len(pipelines)} pipeline(s)")
        sys.exit(ExitCode.OK)

    # Handle confirmation for destructive operations (CLI responsibility)
    if run_type in ("rebuild", "backfill") and not dry_run and not yes:
        echo_warning(
            f"{run_type} will clear existing data for {len(pipelines)} pipelines."
        )
        echo_info("Pipelines to be affected:")
        for pipeline in pipelines:
            echo_info(f"  - {pipeline}")
        if not click.confirm("\nDo you want to continue?"):
            echo_info("Operation cancelled.")
            sys.exit(ExitCode.OK)

    # Show what we're about to do
    if dry_run:
        echo_info(f"[DRY-RUN] Would run {len(pipelines)} pipeline(s) for '{source}':")
    else:
        echo_info(f"Running {len(pipelines)} pipeline(s) for '{source}':")

    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")

    # Build options
    options = RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )

    # Run pipelines
    try:
        batch_result = asyncio.run(_run_all_pipelines_async(pipelines, options))
    except KeyboardInterrupt:
        echo_warning("Batch run interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as e:
        echo_error("Unexpected error during batch execution", str(e))
        sys.exit(ExitCode.FAIL)

    # Output summary
    _echo_batch_summary(batch_result, dry_run)

    # Determine exit code
    if batch_result.all_succeeded:
        sys.exit(ExitCode.OK)
    elif batch_result.failed > 0:
        sys.exit(ExitCode.PIPELINE_ERROR)
    else:
        # All skipped (shutdown)
        sys.exit(ExitCode.SIGINT)


__all__ = [
    "BatchRunResult",
    "run_all",
]
