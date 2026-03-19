"""Private runtime helpers for CLI run command orchestration."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from bioetl.application.services import RunOptions, RunResult
from bioetl.application.services.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.composition import PipelineRegistry
from bioetl.composition.services_api import get_pipeline_runner_service
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)
from bioetl.interfaces.cli.commands.domains.run.command_policy import RunCommandInput

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Protocol

    from bioetl.application.services.cli_run_orchestration_contracts import (
        RunPreparedPipelineCallable,
    )

    class PipelineRunnerService(Protocol):
        """Protocol for pipeline runner services used by CLI runtime helpers."""

        async def run(
            self,
            pipeline: str,
            *,
            options: RunOptions,
        ) -> RunResult: ...


def build_run_command_input(
    *,
    pipeline: str,
    run_type: str,
    resume: bool,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    health_server: bool,
    health_port: int,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
) -> RunCommandInput:
    """Build normalized CLI payload for policy-based execution."""
    return RunCommandInput(
        pipeline=pipeline,
        run_type=run_type,
        resume=resume,
        start_offset=start_offset,
        limit=limit,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        dry_run=dry_run,
        yes=yes,
        vacuum_after_run=vacuum_after_run,
        vacuum_retention_days=vacuum_retention_days,
        debug=debug,
        health_server=health_server,
        health_port=health_port,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
    )


async def run_pipeline_async(
    pipeline: str,
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    registry: PipelineRegistry | None = None,
    *,
    metrics_starter: Callable[[], bool | None] = ensure_metrics_server_started,
    health_context_factory: Callable[
        ..., AbstractAsyncContextManager[object]
    ] = health_server_context,
    runner_service_factory: Callable[
        ..., PipelineRunnerService
    ] = get_pipeline_runner_service,
) -> RunResult:
    """Execute run pipeline request through service with health/metrics context."""
    metrics_starter()
    async with health_context_factory(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = runner_service_factory(registry=registry)
        return await service.run(pipeline, options=options)


async def run_prepared_request_async(
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
    *,
    run_pipeline_async_callable: Callable[
        ..., Awaitable[RunResult]
    ] = run_pipeline_async,
) -> RunResult:
    """Execute a prepared request through the canonical runtime helper path."""
    return await run_pipeline_async_callable(
        request.pipeline,
        request.options,
        health_server_enabled=request.health_server,
        health_port=request.health_port,
        registry=registry,
    )


def build_run_pipeline_callable(
    registry: PipelineRegistry | None = None,
    *,
    run_pipeline_async_callable: Callable[
        ..., Awaitable[RunResult]
    ] = run_pipeline_async,
) -> RunPreparedPipelineCallable:
    """Return a stable async callable for prepared execution requests."""

    async def _run(request: RunExecutionRequest) -> RunResult:
        return await run_prepared_request_async(
            request,
            registry=registry,
            run_pipeline_async_callable=run_pipeline_async_callable,
        )

    return _run
