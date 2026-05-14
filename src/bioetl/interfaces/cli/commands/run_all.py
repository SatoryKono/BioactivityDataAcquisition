"""Run-all CLI command."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

import click

import bioetl.interfaces.cli.commands.domains.run_all.support as run_all_support
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.domains.run.support import (
    build_cli_registry,
    resolve_context_registry,
)
from bioetl.interfaces.cli.commands.domains.run_all.command_entrypoint import (
    build_run_all_click_command,
)
from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
    build_run_all_command_input,
    exit_with_code,
    handle_run_all_cli_failure,
    run_all_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    RunAllBatchExecutionRequest,
    RunAllPolicyRequest,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    run_all_pipelines_async as _run_all_pipelines_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    run_batch_with_policy as _run_batch_with_policy_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    emit_run_all_listing,
    emit_run_all_preview,
    should_prompt_for_destructive_run,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    echo_batch_summary as _echo_batch_summary_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    handle_destructive_confirmation as _handle_destructive_confirmation_impl,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as _impl

    return _impl(registry=registry)


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
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
    return await _run_all_pipelines_async_impl(
        RunAllBatchExecutionRequest(
            pipelines=pipelines,
            options=options,
            health_server_enabled=health_server_enabled,
            health_port=health_port,
            registry=registry,
        ),
        get_pipeline_runner_service_fn=get_pipeline_runner_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        health_server_context_factory=health_server_context,
    )


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary.

    Args:
        result: BatchRunResult with aggregate counts for the completed batch.
        dry_run: When True, prints a dry-run preview summary instead of execution stats.
    """
    _echo_batch_summary_impl(
        result=result,
        dry_run=dry_run,
        info_printer=echo_info,
        error_printer=echo_error,
    )


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
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return True
    return _handle_destructive_confirmation_impl(
        run_type=run_type,
        pipelines=pipelines,
        dry_run=dry_run,
        yes=yes,
        confirm_fn=click.confirm,
        info_printer=echo_info,
        exit_func=exit_with_code,
    )


def _run_batch_with_policy(
    *,
    source: str,
    pipelines: list[str],
    options: RunOptions,
    health_server: bool,
    health_port: int,
    registry: PipelineRegistry | None = None,
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
    return _run_batch_with_policy_impl(
        RunAllPolicyRequest(
            source=source,
            execution=RunAllBatchExecutionRequest(
                pipelines=pipelines,
                options=options,
                health_server_enabled=health_server,
                health_port=health_port,
                registry=registry,
            ),
        ),
        get_pipeline_runner_service_fn=get_pipeline_runner_service,
        ensure_metrics_server_started_fn=ensure_metrics_server_started,
        health_server_context_factory=health_server_context,
        run_coro=asyncio.run,
        handle_failure=lambda exc, source, reason_code: handle_run_all_cli_failure(
            exc,
            source=source,
            reason_code=reason_code,
        ),
    )


def _run_all_callback(
    click_context: click.Context,
    /,
    **options: object,
) -> None:
    """Canonical callback implementation for the run-all Click command."""
    cli_input = _build_run_all_command_input_from_options(options)
    dispatch_cli_callback(
        click_context,
        build_cli_input=lambda: cli_input,
        run_with_cli_policy=_run_all_with_cli_policy,
    )


def _build_run_all_command_input_from_options(
    options: Mapping[str, object],
) -> RunAllCommandInput:
    """Build typed run-all input from Click's object-valued kwargs mapping."""
    return build_run_all_command_input(
        source=cast("str", options["source"]),
        run_type=cast("str", options["run_type"]),
        limit=cast(int | None, options["limit"]),
        dry_run=cast("bool", options["dry_run"]),
        yes=cast("bool", options["yes"]),
        list_only=cast("bool", options["list_only"]),
        debug=cast("bool", options["debug"]),
        health_server=cast("bool", options["health_server"]),
        health_port=cast("int", options["health_port"]),
    )


def _run_all_with_cli_policy(
    click_context: click.Context,
    cli_input: RunAllCommandInput,
) -> None:
    """Resolve registry and execute the prepared run-all policy flow."""
    registry = resolve_context_registry(click_context)
    run_all_command_flow(
        cli_input=cli_input,
        registry=registry,
        destructive_confirmation=_handle_destructive_confirmation,
        listing_emitter=emit_run_all_listing,
        preview_emitter=emit_run_all_preview,
        health_info_presenter=echo_health_server_info,
        execute_batch=_run_batch_with_policy,
        summary_presenter=_echo_batch_summary,
        determine_exit_code=run_all_support.determine_batch_exit_code,
        exit_func=exit_with_code,
    )


run_all = build_run_all_click_command(
    default_health_server_port=DEFAULT_HEALTH_SERVER_PORT,
    run_callback=_run_all_callback,
)


__all__ = [
    "BatchRunResult",
    "build_cli_registry",
    "run_all",
]
