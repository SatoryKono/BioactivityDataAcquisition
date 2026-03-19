"""Execution helpers for the run-all CLI command."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunnerService,
    RunOptions,
    RunResult,
)
from bioetl.composition import PipelineRegistry
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.run_all_helpers import (
    BatchRunResult,
    record_pipeline_failure,
    record_pipeline_result,
)

_EnsureMetricsServerStartedFn = Callable[[], object]
_HealthServerContextFactory = Callable[..., AbstractAsyncContextManager[object]]
_RunAllFailureHandler = Callable[[BaseException, str, str], None]
_RunAllCoroutineRunner = Callable[
    [Coroutine[object, object, BatchRunResult]],
    BatchRunResult,
]


class _GetPipelineRunnerServiceFn(Protocol):
    """Callable protocol for resolving the pipeline runner service."""

    def __call__(
        self,
        *,
        registry: PipelineRegistry | None = None,
    ) -> PipelineRunnerService:
        """Return the pipeline runner service for the selected registry."""
        ...


@dataclass(frozen=True, slots=True)
class RunAllBatchExecutionRequest:
    """Input for one run-all batch execution."""

    pipelines: list[str]
    options: RunOptions
    health_server_enabled: bool = True
    health_port: int = DEFAULT_HEALTH_SERVER_PORT
    registry: PipelineRegistry | None = None


@dataclass(frozen=True, slots=True)
class RunAllPolicyRequest:
    """Input for one run-all CLI policy execution."""

    source: str
    execution: RunAllBatchExecutionRequest


async def _run_pipeline_async(
    service: PipelineRunnerService,
    pipeline: str,
    options: RunOptions,
) -> RunResult:
    """Run a single pipeline asynchronously."""
    return await service.run(pipeline, options=options)


async def _run_pipelines_batch(
    service: PipelineRunnerService,
    pipelines: list[str],
    options: RunOptions,
) -> BatchRunResult:
    """Run pipelines sequentially within one service context."""
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            result = await _run_pipeline_async(service, pipeline, options)
            if record_pipeline_result(
                batch_result=batch_result,
                pipeline=pipeline,
                result=result,
            ):
                break
        except PipelineNotFoundError as exc:
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: not found",
                detail=str(exc),
            )
        except (BioETLError, OSError, RuntimeError, ValueError) as exc:
            error_msg = (
                f"{exc} (reason_code=CLI_RUN_ALL_PIPELINE_ERROR, "
                f"pipeline={pipeline}, error_type={type(exc).__name__})"
            )
            record_pipeline_failure(
                batch_result=batch_result,
                pipeline=pipeline,
                title=f"[FAIL] {pipeline}: unexpected error",
                detail=error_msg,
            )

    return batch_result


async def run_all_pipelines_async(
    request: RunAllBatchExecutionRequest,
    *,
    get_pipeline_runner_service_fn: _GetPipelineRunnerServiceFn,
    ensure_metrics_server_started_fn: _EnsureMetricsServerStartedFn,
    health_server_context_factory: _HealthServerContextFactory,
) -> BatchRunResult:
    """Run all pipelines sequentially with the configured CLI integrations."""
    ensure_metrics_server_started_fn()

    async with health_server_context_factory(
        enabled=request.health_server_enabled,
        port=request.health_port,
    ):
        service = get_pipeline_runner_service_fn(registry=request.registry)
        return await _run_pipelines_batch(service, request.pipelines, request.options)


def run_batch_with_policy(
    request: RunAllPolicyRequest,
    *,
    get_pipeline_runner_service_fn: _GetPipelineRunnerServiceFn,
    ensure_metrics_server_started_fn: _EnsureMetricsServerStartedFn,
    health_server_context_factory: _HealthServerContextFactory,
    run_coro: _RunAllCoroutineRunner,
    handle_failure: _RunAllFailureHandler,
) -> BatchRunResult | None:
    """Execute the run-all batch with typed CLI exception handling."""
    coro = run_all_pipelines_async(
        request.execution,
        get_pipeline_runner_service_fn=get_pipeline_runner_service_fn,
        ensure_metrics_server_started_fn=ensure_metrics_server_started_fn,
        health_server_context_factory=health_server_context_factory,
    )
    try:
        return run_coro(coro)
    except PipelineNotFoundError as exc:
        handle_failure(exc, request.source, "CLI_RUN_ALL_CONFIG_ERROR")
    except BioETLError as exc:
        handle_failure(exc, request.source, "CLI_RUN_ALL_DOMAIN_ERROR")
    except KeyboardInterrupt as exc:
        handle_failure(exc, request.source, "CLI_RUN_ALL_SIGINT")
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        handle_failure(exc, request.source, "CLI_RUN_ALL_UNEXPECTED_ERROR")
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None
