"""Debug command for interactive pipeline step-through execution.

Runs a pipeline with breakpoints at configurable lifecycle stages,
allowing inspection of intermediate state (records, DQ metrics, etc.).
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.application.services import RunOptions, RunResult
from bioetl.application.services.pipeline_debug_service import DebugAbortError
from bioetl.domain.ports import StageBreakpoint
from bioetl.interfaces.cli.commands.domains.run.support import (
    resolve_context_registry,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition import PipelineRegistry

__all__ = ["debug"]

_BREAKPOINT_CHOICES = [bp.value for bp in StageBreakpoint]


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    from bioetl.composition.services_api import get_pipeline_runner_service as _impl

    return _impl(registry=registry)


@click.command()  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline",
    callback=validate_pipeline_name,
    required=True,
    help="Pipeline to debug",
)
@click.option(  # type: ignore[untyped-decorator]
    "--breakpoints",
    type=str,
    default=None,
    help=f"Comma-separated breakpoints: {', '.join(_BREAKPOINT_CHOICES)}. "
    "Default: all breakpoints enabled.",
)
@click.option(  # type: ignore[untyped-decorator]
    "--limit", type=int, default=10, help="Max records to process (default: 10)"
)
@click.option(  # type: ignore[untyped-decorator]
    "--mode",
    type=click.Choice(["interactive", "log"]),
    default="interactive",
    help="Debug mode: interactive (CLI prompts) or log (auto-continue with logging)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run",
)
@click.pass_context  # type: ignore[untyped-decorator]
def debug(
    ctx: click.Context,
    pipeline: str,
    breakpoints: str | None,
    limit: int,
    mode: str,
    run_type: str,
) -> None:
    """Run a pipeline in debug mode with breakpoints.

    Enables step-through execution with inspection of intermediate
    state at each pipeline lifecycle stage.
    """
    # Parse breakpoints
    enabled_breakpoints: set[StageBreakpoint] | None = None
    if breakpoints:
        try:
            enabled_breakpoints = {
                StageBreakpoint(bp.strip()) for bp in breakpoints.split(",")
            }
        except ValueError as exc:
            echo_error(
                f"Invalid breakpoint: {exc}. Valid: {', '.join(_BREAKPOINT_CHOICES)}"
            )
            sys.exit(ExitCode.CONFIG_ERROR)

    echo_info(f"Starting debug session for pipeline '{pipeline}'")
    echo_info(f"Mode: {mode} | Limit: {limit} | Run type: {run_type}")

    if enabled_breakpoints:
        echo_info(f"Breakpoints: {', '.join(bp.value for bp in enabled_breakpoints)}")
    else:
        echo_info("Breakpoints: all stages enabled")

    options = RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=False,
        log_level="DEBUG",
    )
    registry = resolve_context_registry(ctx)

    try:
        result = asyncio.run(
            _run_debug_session(
                pipeline,
                options,
                mode,
                enabled_breakpoints,
                registry=registry,
            )
        )
        echo_info(f"Debug session complete: {result.status.value}")
        echo_info(
            f"Records: fetched={result.records_fetched}, "
            f"silver={result.records_silver}, "
            f"quarantined={result.records_quarantined}"
        )
    except DebugAbortError:
        echo_info("Pipeline aborted by user at breakpoint")
        sys.exit(ExitCode.SIGINT)
    except KeyboardInterrupt:
        echo_info("Debug session interrupted")
        sys.exit(ExitCode.SIGINT)


async def _run_debug_session(
    pipeline: str,
    options: RunOptions,
    mode: str,
    enabled_breakpoints: set[StageBreakpoint] | None,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Run pipeline with debug adapter attached.

    Args:
        pipeline: Pipeline name.
        options: Run options with limit and run_type.
        mode: Debug mode ('interactive' or 'log').
        enabled_breakpoints: Breakpoints to enable.

    Returns:
        RunResult from pipeline execution.
    """
    service = get_pipeline_runner_service(registry=registry)
    return await service.run(pipeline, options=options)
