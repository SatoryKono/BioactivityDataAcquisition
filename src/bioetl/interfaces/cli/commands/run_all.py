"""Run-all CLI public command seam."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

import click

import bioetl.interfaces.cli.commands.domains.run_all.support as run_all_support
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.interfaces.cli.commands.domains.run_all.command_entrypoint import (
    build_run_all_click_command,
)
from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
    build_run_all_command_input,
    exit_with_code,
    run_all_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run_all.public_runtime import (
    RunAllBatchRuntime,
    RunAllCallbackRuntime,
    RunAllPolicyRuntime,
    RunAllPresentationRuntime,
    default_batch_runtime,
    echo_batch_summary_with_runtime,
    handle_destructive_confirmation_with_runtime,
    load_pipeline_runner_service,
    run_all_pipelines_async_with_runtime,
    run_batch_with_policy_runtime,
)
from bioetl.interfaces.cli.commands.domains.run_all.public_runtime import (
    build_run_all_command_input_from_options as _build_input_from_options_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.runtime_boundaries import (
    DEFAULT_HEALTH_SERVER_PORT,
    build_cli_registry,
    build_observability_backend_required_probe_paths,
    echo_error,
    echo_health_server_info,
    echo_info,
    ensure_metrics_server_started,
    ensure_observability_backend_started,
    health_server_context,
    resolve_context_registry,
    should_disable_transient_health_server,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    emit_run_all_listing,
    emit_run_all_preview,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    return load_pipeline_runner_service(registry=registry)


def _batch_runtime() -> RunAllBatchRuntime:
    """Build batch runtime from public patchable seams."""
    return replace(
        default_batch_runtime(
            ensure_metrics_server_started=ensure_metrics_server_started,
            get_pipeline_runner_service=get_pipeline_runner_service,
            health_server_context_factory=health_server_context,
        ),
        run_coro=asyncio.run,
    )


def _presentation_runtime() -> RunAllPresentationRuntime:
    """Build presentation runtime from public patchable seams."""
    return RunAllPresentationRuntime(
        confirm=click.confirm,
        error_printer=echo_error,
        exit_func=exit_with_code,
        info_printer=echo_info,
    )


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server."""
    return await run_all_pipelines_async_with_runtime(
        pipelines,
        options,
        health_server_enabled=health_server_enabled,
        health_port=health_port,
        registry=registry,
        runtime=_batch_runtime(),
    )


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary."""
    echo_batch_summary_with_runtime(
        result,
        dry_run,
        runtime=_presentation_runtime(),
    )


def _handle_destructive_confirmation(
    run_type: str, pipelines: list[str], dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for destructive operations."""
    return handle_destructive_confirmation_with_runtime(
        run_type,
        pipelines,
        dry_run,
        yes,
        runtime=_presentation_runtime(),
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
    """Execute async batch run with typed exception policy."""
    return run_batch_with_policy_runtime(
        source=source,
        pipelines=pipelines,
        options=options,
        health_server=health_server,
        health_port=health_port,
        registry=registry,
        runtime=_batch_runtime(),
    )


def _build_run_all_command_input_from_options(
    options: Mapping[str, object],
) -> RunAllCommandInput:
    """Build typed run-all input from Click's object-valued kwargs mapping."""
    return _build_input_from_options_impl(
        options,
        build_input=build_run_all_command_input,
    )


def _callback_runtime() -> RunAllCallbackRuntime:
    """Build callback runtime from public patchable seams."""
    return RunAllCallbackRuntime(
        build_probe_paths=build_observability_backend_required_probe_paths,
        build_input=build_run_all_command_input,
        disable_transient_health_server=should_disable_transient_health_server,
        ensure_observability_backend_started=ensure_observability_backend_started,
        run_with_cli_policy=_run_all_with_cli_policy,
    )


def _run_all_callback(
    click_context: click.Context,
    /,
    **options: object,
) -> None:
    """Canonical callback implementation for the run-all Click command."""
    cli_input = _build_run_all_command_input_from_options(options)
    if not cli_input.list_only and not cli_input.dry_run:
        backend_result = ensure_observability_backend_started(
            enabled=cli_input.ensure_observability_backend,
            port=cli_input.observability_backend_port,
            required_probe_paths=build_observability_backend_required_probe_paths(),
        )
        if should_disable_transient_health_server(
            health_server_enabled=cli_input.health_server,
            health_port=cli_input.health_port,
            observability_backend_port=cli_input.observability_backend_port,
            backend_result=backend_result,
        ):
            cli_input = replace(cli_input, health_server=False)

    dispatch_cli_callback(
        click_context,
        build_cli_input=lambda: cli_input,
        run_with_cli_policy=_run_all_with_cli_policy,
    )


def _policy_runtime() -> RunAllPolicyRuntime:
    """Build policy runtime from public patchable seams."""
    return RunAllPolicyRuntime(
        build_cli_registry=build_cli_registry,
        destructive_confirmation=_handle_destructive_confirmation,
        determine_exit_code=run_all_support.determine_batch_exit_code,
        execute_batch=_run_batch_with_policy,
        health_info_presenter=echo_health_server_info,
        resolve_context_registry=resolve_context_registry,
        summary_presenter=_echo_batch_summary,
    )


def _run_all_with_cli_policy(
    click_context: click.Context,
    cli_input: RunAllCommandInput,
) -> None:
    """Resolve registry and execute the prepared run-all policy flow."""
    registry = resolve_context_registry(click_context) or build_cli_registry()
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
    "dispatch_cli_callback",
    "emit_run_all_listing",
    "emit_run_all_preview",
    "exit_with_code",
    "resolve_context_registry",
    "run_all",
    "run_all_command_flow",
]
