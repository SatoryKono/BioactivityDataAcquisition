"""Private runtime helpers for CLI run command orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services import RunOptions, RunResult
from bioetl.application.services.cli_run_orchestration_service import (
    RunExecutionRequest,
)
from bioetl.composition.registry import PipelineRegistry
from bioetl.composition.services_api import get_pipeline_runner_service
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_command_policy import RunCommandInput

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


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
) -> RunResult:
    """Execute run pipeline request through service with health/metrics context."""
    ensure_metrics_server_started()
    async with health_server_context(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = get_pipeline_runner_service(registry=registry)
        return await service.run(pipeline, options=options)


def build_run_pipeline_callable(
    registry: PipelineRegistry | None = None,
) -> Callable[[RunExecutionRequest], Awaitable[RunResult]]:
    """Return a stable async callable for prepared execution requests."""

    async def _run(request: RunExecutionRequest) -> RunResult:
        return await run_pipeline_async(
            request.pipeline,
            request.options,
            health_server_enabled=request.health_server,
            health_port=request.health_port,
            registry=registry,
        )

    return _run
