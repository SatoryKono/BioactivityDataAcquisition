"""Single-dependency execution collaborators for DependencyCoordinatorService."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol

import polars as pl

from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.domain.composite import DependencyConfig
from bioetl.domain.composite.result import DependencyResult
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort

if TYPE_CHECKING:
    from bioetl.application.composite.dependency_progress_tracker import (
        DependencyProgressService,
    )

__all__ = [
    "execute_dependency_runner",
    "log_dependencies_batch_start",
    "log_dependency_start",
    "run_dependency_batch",
    "run_single_dependency",
]


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
    except Exception as e:
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


class _DependencyBatchHost(Protocol):
    """Host surface for sequential dependency batch execution."""

    _logger: LoggerPort
    _progress_service: DependencyProgressService

    async def _get_effective_keys(
        self,
        dependency: DependencyConfig,
        seed_keys: pl.DataFrame,
        dep_config_lookup: dict[str, DependencyConfig],
    ) -> pl.DataFrame: ...

    async def _run_single_dependency(
        self,
        dependency: DependencyConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> DependencyResult: ...


async def run_dependency_batch(
    host: _DependencyBatchHost,
    *,
    keys: pl.DataFrame,
    dependencies: Sequence[DependencyConfig],
    completed: frozenset[str],
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> dict[str, DependencyResult]:
    """Run dependencies sequentially and return per-pipeline results."""
    results: dict[str, DependencyResult] = {}
    dep_config_lookup = {dependency.pipeline: dependency for dependency in dependencies}

    if not dependencies:
        host._logger.debug("No dependencies to run")
        return results

    log_dependencies_batch_start(logger=host._logger, dependencies=dependencies)

    for dependency in dependencies:
        if host._progress_service.maybe_store_completed_skip(
            dependency=dependency,
            completed=completed,
            results=results,
        ):
            continue

        if host._progress_service.maybe_store_blocked_chain(
            dependency=dependency,
            results=results,
        ):
            if host._progress_service.should_stop_after_result(
                dependency=dependency,
                result=results[dependency.pipeline],
            ):
                break
            continue

        effective_keys = await host._get_effective_keys(
            dependency=dependency,
            seed_keys=keys,
            dep_config_lookup=dep_config_lookup,
        )
        result = await host._run_single_dependency(
            dependency=dependency,
            keys=effective_keys,
            runner_factory=runner_factory,
        )
        results[dependency.pipeline] = result

        if host._progress_service.should_stop_after_result(
            dependency=dependency,
            result=result,
        ):
            break

    return results
