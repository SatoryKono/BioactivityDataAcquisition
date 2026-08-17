"""Permanent public run command seam.

The retained owner package is ``bioetl.interfaces.cli.commands.domains.run``.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING, NoReturn

import click

from bioetl.interfaces.cli.commands._typed_option_values import (
    optional_option,
    require_option,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
    publish_metrics_safely,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started as _ensure_metrics_server_started_impl,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    attach_observability_backend_to_cli_input,
    build_observability_backend_cli_kwargs_from_options,
    build_observability_backend_required_probe_paths,
    ensure_observability_backend_started,
    should_disable_transient_health_server,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    echo_health_server_info as _echo_health_server_info_impl,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    health_server_context as _health_server_context_impl,
)
from bioetl.interfaces.cli.commands.domains.run import (
    runtime_helpers as _run_runtime_helpers,
)
from bioetl.interfaces.cli.commands.domains.run.command_entrypoint import (
    build_run_click_command,
)
from bioetl.interfaces.cli.commands.domains.run.command_policy import (
    RunCommandInput,
    handle_cli_failure,
    map_status_to_exit_code,
    run_command_flow,
)
from bioetl.interfaces.cli.commands.domains.run.result_flow import (
    finalize_run_result as _finalize_run_result_impl,
)
from bioetl.interfaces.cli.commands.domains.run.result_flow import (
    present_run_health_info as _present_run_health_info_impl,
)
from bioetl.interfaces.cli.commands.domains.run.result_presenter import (
    echo_run_result as _echo_run_result,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    build_run_command_input as _build_run_command_input_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    build_run_pipeline_callable as _build_run_pipeline_callable_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    run_pipeline_async as _run_pipeline_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run.runtime_helpers import (
    run_prepared_request_async as _run_prepared_request_async_impl,
)
from bioetl.interfaces.cli.commands.domains.run.service_access import (
    create_cli_run_orchestration_service as _create_cli_run_orchestration_service_impl,
)
from bioetl.interfaces.cli.commands.domains.run.service_access import (
    get_cli_run_orchestration_service as _get_cli_run_orchestration_service_impl,
)
from bioetl.interfaces.cli.commands.domains.run.support import (
    resolve_context_registry,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services.execution.cli_run_orchestration_models import (
        CliRunOptionsInput,
        RunExecutionRequest,
    )
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        RunOptions,
        RunResult,
    )
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "build_run_options",
    "create_cli_run_orchestration_service",
    "execute_run",
    "get_cli_run_orchestration_service",
    "handle_cli_failure",
    "run",
    "validate_options",
]

# Inventory of retained run-command seams. Update tests alongside intentional changes.
_RUN_CANONICAL_BOUNDARY_SEAMS = (
    "create_cli_run_orchestration_service",
    "get_cli_run_orchestration_service",
    "_build_run_command_input",
    "_build_run_pipeline_callable",
    "_map_status_to_exit_code",
    "_present_run_health_info",
    "_finalize_run_result",
    "_run_pipeline_async",
    "_run_prepared_request_async",
)


def get_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Return process-local run orchestration service accessor."""
    return _get_cli_run_orchestration_service_impl()


def create_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Build a fresh run orchestration service for one CLI command execution."""
    return _create_cli_run_orchestration_service_impl()


def _exit_with_code(code: int | str | None = None) -> NoReturn:
    """Typed wrapper around sys.exit for policy flow injection."""
    sys.exit(code)


def validate_options(start_offset: int | None, run_type: str, resume: bool) -> None:
    """Validate --start-offset constraints; sys.exit on error."""
    validation = create_cli_run_orchestration_service().validate_start_offset(
        start_offset=start_offset,
        run_type=run_type,
        resume=resume,
    )
    if validation.is_valid:
        return
    echo_error(validation.error_message or "Invalid run options")
    sys.exit(ExitCode.CONFIG_ERROR)


def build_run_options(options_input: CliRunOptionsInput) -> RunOptions:
    """Build RunOptions from CLI parameters."""
    return create_cli_run_orchestration_service().build_options(options_input)


def execute_run(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Execute run and flush metrics at command boundary."""
    return create_cli_run_orchestration_service().execute_pipeline(
        request=request,
        run_pipeline_async=_build_run_pipeline_callable(
            registry=registry,
            run_pipeline_async_callable=_run_pipeline_async,
        ),
        run_coroutine=asyncio.run,
        flush_metrics=publish_metrics_safely,
    )


_build_run_command_input = _build_run_command_input_impl
_map_status_to_exit_code = map_status_to_exit_code
_build_run_pipeline_callable = _build_run_pipeline_callable_impl


def _present_run_health_info(request: RunExecutionRequest) -> None:
    """Render health-server info for a prepared run request."""
    _present_run_health_info_impl(
        request,
        info_presenter=echo_health_server_info,
    )


def _finalize_run_result(result: RunResult) -> None:
    """Render CLI run result and terminate with the canonical exit code."""
    _finalize_run_result_impl(
        result,
        presenter=_echo_run_result,
        status_mapper=_map_status_to_exit_code,
        exit_func=_exit_with_code,
    )


def _run_command_with_cli_policy(
    ctx: click.Context,
    cli_input: RunCommandInput,
) -> None:
    """Execute the prepared run command through the canonical CLI policy path."""
    cli_input = attach_observability_backend_to_cli_input(
        cli_input,
        required_probe_paths=build_observability_backend_required_probe_paths(
            pipelines=(cli_input.pipeline,)
        ),
        ensure_backend_started_fn=ensure_observability_backend_started,
        disable_transient_health_server_fn=should_disable_transient_health_server,
    )

    registry = resolve_context_registry(ctx)
    service = create_cli_run_orchestration_service()
    run_command_flow(
        cli_input=cli_input,
        service=service,
        execute_run=partial(execute_run, registry=registry),
        health_info_presenter=_present_run_health_info,
        result_finalizer=_finalize_run_result,
        exit_func=_exit_with_code,
    )


async def _run_pipeline_async(
    pipeline: str,
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Run pipeline asynchronously via service."""
    return await _run_pipeline_async_impl(
        pipeline,
        options,
        health_server_enabled=health_server_enabled,
        health_port=health_port,
        registry=registry,
        metrics_starter=ensure_metrics_server_started,
        health_context_factory=health_server_context,
        runner_service_factory=_run_runtime_helpers.get_pipeline_runner_service,
    )


async def _run_prepared_request_async(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Execute a prepared CLI run request via the canonical async runtime path."""
    return await _run_prepared_request_async_impl(
        request,
        registry=registry,
        run_pipeline_async_callable=_run_pipeline_async,
    )


def _build_run_command_input_from_options(
    options: Mapping[str, object],
) -> RunCommandInput:
    """Build typed run-command input from Click's object-valued kwargs mapping."""
    backend_options = build_observability_backend_cli_kwargs_from_options(
        options,
        default_port=DEFAULT_HEALTH_SERVER_PORT,
    )
    return RunCommandInput(
        pipeline=require_option(options, "pipeline", str),
        run_type=require_option(options, "run_type", str),
        resume=require_option(options, "resume", bool),
        start_offset=optional_option(options, "start_offset", int),
        limit=optional_option(options, "limit", int),
        input_csv=optional_option(options, "input_csv", str),
        filter_column=optional_option(options, "filter_column", str),
        filter_field=optional_option(options, "filter_field", str),
        dry_run=require_option(options, "dry_run", bool),
        yes=require_option(options, "yes", bool),
        vacuum_after_run=optional_option(options, "vacuum_after_run", bool),
        vacuum_retention_days=optional_option(options, "vacuum_retention_days", int),
        debug=require_option(options, "debug", bool),
        health_server=require_option(options, "health_server", bool),
        health_port=require_option(options, "health_port", int),
        ensure_observability_backend=backend_options.ensure_observability_backend,
        observability_backend_port=backend_options.observability_backend_port,
        enable_tracing=optional_option(options, "enable_tracing", bool),
        use_cached_bronze=require_option(options, "use_cached_bronze", bool),
        cached_bronze_date=optional_option(options, "cached_bronze_date", str),
        cached_bronze_path=optional_option(options, "cached_bronze_path", str),
        replay_of_run_id=optional_option(options, "replay_of_run_id", str),
        replay_of_manifest_id=optional_option(options, "replay_of_manifest_id", str),
        resume_run_id=optional_option(options, "resume_run_id", str),
        resume_manifest_id=optional_option(options, "resume_manifest_id", str),
        exact_replay=require_option(options, "exact_replay", bool),
        required_persistence_profile=optional_option(
            options, "required_persistence_profile", str
        ),
    )


def _run_callback(ctx: click.Context, /, **options: object) -> None:
    """Canonical callback implementation for the run Click command."""
    cli_input = _build_run_command_input_from_options(options)
    if cli_input.exact_replay and not cli_input.use_cached_bronze:
        echo_warning(
            "Strict exact replay requires snapshot-backed cached Bronze inputs; "
            "without --use-cached-bronze this run is outside the strict exact-replay boundary."
        )

    dispatch_cli_callback(
        ctx,
        build_cli_input=lambda: _build_run_command_input(cli_input),
        run_with_cli_policy=_run_command_with_cli_policy,
    )


run = build_run_click_command(
    validate_pipeline_name=validate_pipeline_name,
    default_health_server_port=DEFAULT_HEALTH_SERVER_PORT,
    run_callback=_run_callback,
)


echo_health_server_info = _echo_health_server_info_impl
ensure_metrics_server_started = _ensure_metrics_server_started_impl
health_server_context = _health_server_context_impl
