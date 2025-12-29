"""Helper functions for the run command.

Provides validation, confirmation, and preview utilities for pipeline execution.
These are CLI-layer responsibilities separated for maintainability.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

__all__ = [
    "get_runner_logger",
    "handle_destructive_run_confirmation",
    "show_cleanup_preview",
    "validate_pipeline_name",
]

from bioetl.composition.entrypoints import preview_cleanup
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_warning,
)

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.ports import LoggerPort


def validate_pipeline_name(
    _ctx: click.Context | None, _param: click.Parameter | None, value: str
) -> str:
    """Validate pipeline name against the registry at runtime.

    Args:
        _ctx: Click context (unused).
        _param: Click parameter (unused).
        value: Pipeline name to validate.

    Returns:
        Validated pipeline name.

    Raises:
        click.BadParameter: If pipeline name is not in registry.
    """
    registry = get_default_registry()
    available = registry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


def get_runner_logger(runner: PipelineRunner) -> LoggerPort | None:
    """Get logger from runner with fallback.

    Args:
        runner: PipelineRunner instance.

    Returns:
        Logger instance (LoggerPort) or None if not found.
    """
    logger = getattr(runner, "logger", None)
    if logger is None:
        logger = getattr(runner, "_logger", None)
    return logger


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Args:
        pipeline: Pipeline name.
    """
    preview_result = await preview_cleanup(pipeline)
    echo_cleanup_preview(preview_result)


def show_cleanup_preview(pipeline: str) -> None:
    """Show cleanup preview synchronously.

    Args:
        pipeline: Pipeline name.
    """
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except Exception as e:
        echo_error("Error previewing cleanup", str(e))


def handle_destructive_run_confirmation(
    pipeline: str, run_type: str, dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for rebuild/backfill runs.

    Args:
        pipeline: Pipeline name.
        run_type: Type of run.
        dry_run: Whether this is a dry run.
        yes: Whether to skip confirmation.

    Returns:
        True if should continue with pipeline execution, False if should exit early.
    """
    if run_type not in ("rebuild", "backfill"):
        return True

    if dry_run:
        echo_dry_run_prefix(f"Would clear data for pipeline: {pipeline}")
        echo_dry_run_prefix(f"Run type: {run_type}")
        show_cleanup_preview(pipeline)
        return False

    if not yes:
        echo_warning(f"{run_type} will clear existing data for {pipeline}.")
        if not click.confirm("Do you want to continue?"):
            echo_info("Operation cancelled.")
            sys.exit(0)

    return True
