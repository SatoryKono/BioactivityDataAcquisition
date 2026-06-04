"""Public run-all seam runtime orchestration helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import click

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
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
    run_all_pipelines_async,
)
from bioetl.interfaces.cli.commands.domains.run_all.execution import (
    run_batch_with_policy as run_batch_with_policy_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.public_runtime_deps import (
    RunAllBatchRuntime,
    RunAllCallbackRuntime,
    RunAllPolicyRuntime,
    RunAllPresentationRuntime,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    emit_run_all_listing,
    emit_run_all_preview,
    should_prompt_for_destructive_run,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    echo_batch_summary as echo_batch_summary_impl,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    handle_destructive_confirmation as handle_destructive_confirmation_impl,
)
from bioetl.interfaces.cli.commands.domains.shared.callback_dispatch import (
    dispatch_cli_callback,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition.registry_api import PipelineRegistry


def load_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Load the pipeline runner service through composition on demand."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as impl

    return impl(registry=registry)


async def run_all_pipelines_async_with_runtime(
    pipelines: list[str],
    options: RunOptions,
    *,
    health_server_enabled: bool,
    health_port: int,
    registry: PipelineRegistry | None,
    runtime: RunAllBatchRuntime,
) -> BatchRunResult:
    return await run_all_pipelines_async(
        RunAllBatchExecutionRequest(
            pipelines=pipelines,
            options=options,
            health_server_enabled=health_server_enabled,
            health_port=health_port,
            registry=registry,
        ),
        get_pipeline_runner_service_fn=runtime.get_pipeline_runner_service,
        ensure_metrics_server_started_fn=runtime.ensure_metrics_server_started,
        health_server_context_factory=runtime.health_server_context_factory,
    )


def echo_batch_summary_with_runtime(
    result: BatchRunResult,
    dry_run: bool,
    *,
    runtime: RunAllPresentationRuntime,
) -> None:
    echo_batch_summary_impl(
        result=result,
        dry_run=dry_run,
        info_printer=runtime.info_printer,
        error_printer=runtime.error_printer,
    )


def handle_destructive_confirmation_with_runtime(
    run_type: str,
    pipelines: list[str],
    dry_run: bool,
    yes: bool,
    *,
    runtime: RunAllPresentationRuntime,
) -> bool:
    if not should_prompt_for_destructive_run(
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return True
    return handle_destructive_confirmation_impl(
        run_type=run_type,
        pipelines=pipelines,
        dry_run=dry_run,
        yes=yes,
        confirm_fn=runtime.confirm,
        info_printer=runtime.info_printer,
        exit_func=runtime.exit_func,
    )


def run_batch_with_policy_runtime(
    *,
    source: str,
    pipelines: list[str],
    options: RunOptions,
    health_server: bool,
    health_port: int,
    registry: PipelineRegistry | None,
    runtime: RunAllBatchRuntime,
) -> BatchRunResult | None:
    """Execute async batch run with typed exception policy."""
    return run_batch_with_policy_impl(
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
        get_pipeline_runner_service_fn=runtime.get_pipeline_runner_service,
        ensure_metrics_server_started_fn=runtime.ensure_metrics_server_started,
        health_server_context_factory=runtime.health_server_context_factory,
        run_coro=runtime.run_coro,
        handle_failure=runtime.handle_failure,
    )


def build_run_all_command_input_from_options(
    options: Mapping[str, object],
    *,
    build_input: Callable[..., RunAllCommandInput] = build_run_all_command_input,
) -> RunAllCommandInput:
    return build_input(
        source=cast("str", options["source"]),
        run_type=cast("str", options["run_type"]),
        limit=cast(int | None, options["limit"]),
        dry_run=cast("bool", options["dry_run"]),
        yes=cast("bool", options["yes"]),
        list_only=cast("bool", options["list_only"]),
        debug=cast("bool", options["debug"]),
        health_server=cast("bool", options["health_server"]),
        health_port=cast("int", options["health_port"]),
        ensure_observability_backend=cast(
            "bool", options.get("ensure_observability_backend", True)
        ),
        observability_backend_port=cast(
            "int", options.get("observability_backend_port", 8081)
        ),
    )


def run_all_callback_runtime(
    click_context: click.Context,
    /,
    *,
    options: Mapping[str, object],
    runtime: RunAllCallbackRuntime,
) -> None:
    cli_input = build_run_all_command_input_from_options(
        options,
        build_input=runtime.build_input,
    )
    if not cli_input.list_only and not cli_input.dry_run:
        backend_result = runtime.ensure_observability_backend_started(
            enabled=cli_input.ensure_observability_backend,
            port=cli_input.observability_backend_port,
            required_probe_paths=runtime.build_probe_paths(),
        )
        if runtime.disable_transient_health_server(
            health_server_enabled=cli_input.health_server,
            health_port=cli_input.health_port,
            observability_backend_port=cli_input.observability_backend_port,
            backend_result=backend_result,
        ):
            cli_input = replace(cli_input, health_server=False)
    dispatch_cli_callback(
        click_context,
        build_cli_input=lambda: cli_input,
        run_with_cli_policy=runtime.run_with_cli_policy,
    )


def run_all_with_cli_policy_runtime(
    click_context: click.Context,
    cli_input: RunAllCommandInput,
    *,
    runtime: RunAllPolicyRuntime,
) -> None:
    registry = (
        runtime.resolve_context_registry(click_context) or runtime.build_cli_registry()
    )
    run_all_command_flow(
        cli_input=cli_input,
        registry=registry,
        destructive_confirmation=runtime.destructive_confirmation,
        listing_emitter=emit_run_all_listing,
        preview_emitter=emit_run_all_preview,
        health_info_presenter=runtime.health_info_presenter,
        execute_batch=runtime.execute_batch,
        summary_presenter=runtime.summary_presenter,
        determine_exit_code=runtime.determine_exit_code,
        exit_func=exit_with_code,
    )


def default_batch_runtime(
    *,
    ensure_metrics_server_started: Callable[[], object],
    get_pipeline_runner_service: Callable[..., PipelineRunnerService],
    health_server_context_factory: Callable[..., object],
) -> RunAllBatchRuntime:
    return RunAllBatchRuntime(
        ensure_metrics_server_started=ensure_metrics_server_started,
        get_pipeline_runner_service=get_pipeline_runner_service,
        handle_failure=lambda exc, source, reason_code: handle_run_all_cli_failure(
            exc,
            source=source,
            reason_code=reason_code,
        ),
        health_server_context_factory=health_server_context_factory,
        run_coro=asyncio.run,
    )
