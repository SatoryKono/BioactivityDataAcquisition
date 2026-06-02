"""Helper functions for the run command.

Provides validation, confirmation, and preview utilities for pipeline execution.
These are CLI-layer responsibilities separated for maintainability.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from functools import cache
from typing import TYPE_CHECKING, cast

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.maintenance.service_access import (
    preview_cleanup as preview_maintenance_cleanup,
)

__all__ = [
    "build_cli_registry",
    "get_runner_logger",
    "handle_destructive_run_confirmation",
    "preview_cleanup",
    "resolve_context_registry",
    "show_cleanup_preview",
    "validate_pipeline_name",
]
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    build_failure_context,
    render_failure_context,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_warning,
)

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.ports import LoggerPort


@cache
def _load_pipeline_registry_type() -> type[PipelineRegistry]:
    """Resolve PipelineRegistry lazily so command imports stay lightweight."""
    from bioetl.composition.registry_api import PipelineRegistry

    return cast("type[PipelineRegistry]", PipelineRegistry)


def build_cli_registry() -> PipelineRegistry:
    """Compatibility seam for tests that patch CLI registry construction."""
    from bioetl.interfaces.cli.registry_helpers import build_cli_registry as _impl

    return _impl()


def _resolve_populated_default_registry() -> PipelineRegistry | None:
    """Retired compatibility seam kept patchable for older CLI unit tests."""
    return None


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Compatibility seam for cleanup preview patched by CLI dry-run tests."""
    impl = cast(
        "Callable[[str], Awaitable[CleanupPreview]]",
        preview_maintenance_cleanup,
    )
    return await impl(pipeline)


def resolve_context_registry(
    click_context: click.Context | None = None,
) -> PipelineRegistry | None:
    """Return the explicit registry carried by Click context, if any."""
    if click_context is None:
        click_context = click.get_current_context(silent=True)
    if click_context is None or click_context.obj is None:
        return None
    pipeline_registry_type = _load_pipeline_registry_type()
    if not isinstance(click_context.obj, pipeline_registry_type):
        return None
    return click_context.obj


def validate_pipeline_name(
    click_context: click.Context | None,
    _param: click.Parameter | None,
    value: str,
) -> str:
    """Validate pipeline name against the registry at runtime.

    Args:
        click_context: Click context; if ``click_context.obj`` is a ``PipelineRegistry``,
            it is used directly, otherwise falls back to a fresh CLI registry.
        _param: Click parameter (unused).
        value: Pipeline name to validate.

    Returns:
        Validated pipeline name.

    Raises:
        click.BadParameter: If pipeline name is not in registry.
    """
    registry = resolve_context_registry(click_context)
    if registry is None:
        registry = _resolve_populated_default_registry()
        if (
            click_context is not None
            and click_context.obj is None
            and registry is not None
        ):
            click_context.obj = registry
    available = list(registry.list_pipelines()) if registry is not None else []
    if not available or value not in available:
        fallback_registry = build_cli_registry()
        fallback_available = list(fallback_registry.list_pipelines())
        if click_context is not None and click_context.obj is None:
            click_context.obj = fallback_registry
        if fallback_available or not available:
            available = fallback_available
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
    except BioETLError as exc:
        failure_context = build_failure_context(
            exc,
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
        )
        echo_error(
            "Error previewing cleanup",
            render_failure_context(failure_context),
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        failure_context = build_failure_context(
            exc,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
        )
        echo_error(
            "Error previewing cleanup",
            render_failure_context(failure_context),
        )


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
        if not click.confirm("Do you want to continue?", default=None):
            echo_info("Operation cancelled.")
            sys.exit(ExitCode.OK)

    return True
