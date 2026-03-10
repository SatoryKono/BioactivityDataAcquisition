"""Debug command for interactive pipeline step-through execution.

Runs a pipeline with breakpoints at configurable lifecycle stages,
allowing inspection of intermediate state (records, DQ metrics, etc.).
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.services import RunOptions, RunResult
from bioetl.application.services.pipeline_debug_service import DebugAbortError
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.domain.ports.runtime.pipeline_debug import StageBreakpoint
from bioetl.interfaces.cli.commands.run_helpers import validate_pipeline_name
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info

__all__ = ["debug"]

_BREAKPOINT_CHOICES = [bp.value for bp in StageBreakpoint]


@click.command()
@click.option(
    "--pipeline",
    callback=validate_pipeline_name,
    required=True,
    help="Pipeline to debug",
)
@click.option(
    "--breakpoints",
    type=str,
    default=None,
    help=f"Comma-separated breakpoints: {', '.join(_BREAKPOINT_CHOICES)}. "
    "Default: all breakpoints enabled.",
)
@click.option(
    "--limit", type=int, default=10, help="Max records to process (default: 10)"
)
@click.option(
    "--mode",
    type=click.Choice(["interactive", "log"]),
    default="interactive",
    help="Debug mode: interactive (CLI prompts) or log (auto-continue with logging)",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run",
)
def debug(
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

    try:
        result = asyncio.run(
            _run_debug_session(pipeline, options, mode, enabled_breakpoints)
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
    from dataclasses import replace

    from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
    from bioetl.infrastructure.observability.debug_adapters import (
        InteractiveDebugAdapter,
        LoggingDebugAdapter,
    )

    # Create debug adapter based on mode
    logger = bootstrap_logger_port(
        pipeline=pipeline,
        run_id=None,  # Will be set by service
        log_level=options.log_level or "DEBUG",
    )

    if mode == "interactive":
        debug_port = InteractiveDebugAdapter(
            enabled_breakpoints=enabled_breakpoints,
            logger=logger,
        )
    else:  # mode == "log"
        debug_port = LoggingDebugAdapter(
            logger=logger,
            enabled_breakpoints=enabled_breakpoints,
        )

    # Add debug_port to options
    options = replace(options, debug_port=debug_port)

    # Get service and run with debug port
    service = get_pipeline_runner_service()
    return await service.run(pipeline, options=options)
