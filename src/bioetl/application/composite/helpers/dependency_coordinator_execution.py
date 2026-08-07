"""Single-dependency execution collaborators for DependencyCoordinatorService."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol

import polars as pl

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.domain.composite.result import DependencyResult
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort

if TYPE_CHECKING:
    from bioetl.application.composite.dependency_result_mapper import (
        DependencyResultService,
    )
    from bioetl.domain.composite import DependencyConfig

__all__ = [
    "execute_dependency_runner",
    "log_dependencies_batch_start",
    "log_dependency_start",
    "run_single_dependency",
]

_DEPENDENCY_EXECUTION_ERRORS = (
    BioETLError,
    NetworkError,
    StorageError,
    CheckpointConflictError,
    DataQualityError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
)


class _DependencyCoordinatorExecutionHost(Protocol):
    """Minimal host surface required for single-dependency execution."""

    _logger: LoggerPort
    _clock: ClockPort
    _result_service: DependencyResultService


def log_dependencies_batch_start(
    *,
    logger: LoggerPort,
    dependencies: Sequence[DependencyConfig],
) -> None:
    """Emit structured start log for dependency batch execution."""
    logger.info(
        "Running dependencies",
        count=len(dependencies),
        dependencies=[dependency.pipeline for dependency in dependencies],
    )


def log_dependency_start(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    keys: pl.DataFrame,
) -> None:
    """Emit structured log entry for dependency start."""
    logger.info(
        "Starting dependency",
        dependency=dependency.pipeline,
        keys_count=len(keys),
        timeout_seconds=dependency.timeout_seconds,
    )


async def execute_dependency_runner(
    *,
    dependency: DependencyConfig,
    keys: pl.DataFrame,
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> ExecutionMetricsRunnerPort:
    """Execute dependency runner under timeout guard."""
    async with asyncio.timeout(dependency.timeout_seconds):
        runner = runner_factory(dependency.pipeline, keys)
        await runner.run()
    return runner


async def run_single_dependency(
    host: _DependencyCoordinatorExecutionHost,
    *,
    dependency: DependencyConfig,
    keys: pl.DataFrame,
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> DependencyResult:
    """Run a single dependency with timeout and error handling."""
    started_at, started_monotonic = capture_runtime_timing_anchor(clock=host._clock)
    log_dependency_start(logger=host._logger, dependency=dependency, keys=keys)
    try:
        runner = await execute_dependency_runner(
            dependency=dependency,
            keys=keys,
            runner_factory=runner_factory,
        )
    except TimeoutError:
        completed_at, duration_seconds = derive_completion_timestamp(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        return host._result_service.build_timeout_result(
            dependency=dependency,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
        )
    except _DEPENDENCY_EXECUTION_ERRORS as e:
        completed_at, duration_seconds = derive_completion_timestamp(
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        return host._result_service.build_failed_result(
            dependency=dependency,
            error=e,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
        )

    completed_at, duration = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )
    return host._result_service.build_success_result(
        dependency=dependency,
        runner=runner,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
    )
