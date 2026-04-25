"""Private runtime helpers for CLI run command orchestration."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
)
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

    from bioetl.application.services.execution.cli_run_orchestration_contracts import (
        RunPreparedPipelineCallable,
    )
    from bioetl.composition.registry_api import PipelineRegistry


class PipelineRunnerService(Protocol):
    """Protocol for pipeline runner services used by CLI runtime helpers."""

    async def run(
        self,
        pipeline: str,
        *,
        options: RunOptions,
    ) -> RunResult: ...


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Resolve the pipeline runner service lazily for CLI runtime helpers."""
    from bioetl.composition.execution_api import get_pipeline_runner_service as _impl

    return cast(PipelineRunnerService, _impl(registry=registry))


def build_run_command_input(
    cli_input: RunCommandInput,
) -> RunCommandInput:
    """Build normalized CLI payload for policy-based execution."""
    return cli_input


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
