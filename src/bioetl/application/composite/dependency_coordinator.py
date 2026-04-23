"""Dependency coordination for seed->dependency key propagation (ADR-026)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.dependency_key_resolvers import (
    ChainedKeyResolver,
    SeedKeyResolver,
)
from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.application.composite.port_types import (
    ClockPort,
    DeltaReaderPort,
    ExecutionMetricsRunnerPort,
    LoggerPort,
)
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

if TYPE_CHECKING:
    from bioetl.domain.composite.config import DependencyConfig


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


__all__ = ["DependencyCoordinatorService"]


def _log_dependencies_batch_start(
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


def _log_dependency_start(
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


class DependencyCoordinatorService:
    """Coordinates dependency pipeline execution.

    Dependencies run sequentially after the seed but before enrichers.
    They populate Silver tables that enrichers will read from.

    Supports chained dependencies where one dependency's output provides
    keys for another. The key_source field in DependencyConfig specifies
    which dependency's Silver table to read keys from.

    Unlike enrichers which run in parallel, dependencies run sequentially
    to avoid overwhelming APIs and ensure predictable ordering.

    Attributes:
        logger: Structured logger.
        progress_service: Service for skip/stop bookkeeping.
        result_service: Service for mapping execution outcomes.
        delta_reader: Reader for Silver tables (for chained dependencies).

    Example:
        >>> coordinator = DependencyCoordinatorService(
        ...     logger=logger,
        ...     seed_key_resolver=seed_key_resolver,
        ...     chained_key_resolver=chained_key_resolver,
        ...     progress_service=progress_service,
        ...     result_service=result_service,
        ...     delta_reader=reader,
        ... )
        >>> results = await coordinator.run_dependencies(
        ...     keys=keys_df,
        ...     dependencies=dependencies,
        ...     completed=frozenset(),
        ...     runner_factory=factory,
        ... )
    """

    def __init__(
        self,
        logger: LoggerPort,
        seed_key_resolver: SeedKeyResolver,
        chained_key_resolver: ChainedKeyResolver,
        progress_service: DependencyProgressService,
        result_service: DependencyResultService,
        delta_reader: DeltaReaderPort | None = None,
        clock: ClockPort | None = None,
    ) -> None:
        """Initialize dependency coordinator.

        Args:
            logger: Structured logger.
            seed_key_resolver: Resolver for seed-key dependencies.
            chained_key_resolver: Resolver for chained dependencies.
            progress_service: Service for dependency progress bookkeeping.
            result_service: Service for dependency result/log assembly.
            delta_reader: Reader for Silver tables (required for chained dependencies).
        """
        self._logger = logger
        self._delta_reader = delta_reader
        self._seed_key_resolver = seed_key_resolver
        self._chained_key_resolver = chained_key_resolver
        self._result_service = result_service
        self._progress_service = progress_service
        self._clock = clock

    async def run_dependencies(
        self,
        keys: pl.DataFrame,
        dependencies: Sequence[DependencyConfig],
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> dict[str, DependencyResult]:
        """Run dependencies sequentially and return per-pipeline results.

        Uses seed keys for standard dependencies and source-table keys for
        chained dependencies (`key_source`). Stops early when a required
        dependency fails.

        Args:
            keys: DataFrame of seed keys passed to each dependency pipeline.
            dependencies: Ordered sequence of dependency configurations to execute.
            completed: Set of pipeline names already completed (skipped when resuming).
            runner_factory: Callable that creates a metrics-readable runner given a
                pipeline name and key DataFrame.

        Returns:
            Mapping from dependency pipeline name to its DependencyResult.
        """
        results: dict[str, DependencyResult] = {}
        dep_config_lookup = {
            dependency.pipeline: dependency for dependency in dependencies
        }

        if not dependencies:
            self._logger.debug(
                "No dependencies to run",
            )
            return results

        _log_dependencies_batch_start(logger=self._logger, dependencies=dependencies)

        for dependency in dependencies:
            if self._progress_service.maybe_store_completed_skip(
                dependency=dependency,
                completed=completed,
                results=results,
            ):
                continue

            effective_keys = await self._get_effective_keys(
                dependency=dependency,
                seed_keys=keys,
                dep_config_lookup=dep_config_lookup,
            )

            result = await self._run_single_dependency(
                dependency=dependency,
                keys=effective_keys,
                runner_factory=runner_factory,
            )
            results[dependency.pipeline] = result

            if self._progress_service.should_stop_after_result(
                dependency=dependency,
                result=result,
            ):
                break

        return results

    async def _get_effective_keys(
        self,
        dependency: DependencyConfig,
        seed_keys: pl.DataFrame,
        dep_config_lookup: dict[str, DependencyConfig],
    ) -> pl.DataFrame:
        """Get effective keys for a dependency.

        For standard dependencies (uses_seed_keys=True), returns seed keys.
        For chained dependencies, reads keys from the key_source's Silver table.

        Args:
            dependency: Current dependency configuration.
            seed_keys: Keys from seed pipeline.
            dep_config_lookup: All dependency configs for finding source tables.

        Returns:
            DataFrame with keys for this dependency.

        Raises:
            ValueError: If chained dependency config is invalid or keys cannot be read.
        """
        resolver = (
            self._seed_key_resolver
            if dependency.uses_seed_keys
            else self._chained_key_resolver
        )
        return await resolver.resolve(
            dependency=dependency,
            seed_keys=seed_keys,
            dep_config_lookup=dep_config_lookup,
            delta_reader=self._delta_reader,
        )

    async def _run_single_dependency(
        self,
        dependency: DependencyConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> DependencyResult:
        """Run a single dependency with timeout and error handling.

        Args:
            dependency: Dependency configuration.
            keys: Keys DataFrame from seed.
            runner_factory: Factory to create a metrics-readable dependency runner.

        Returns:
            DependencyResult with execution outcome.
        """
        started_at, started_monotonic = capture_runtime_timing_anchor(clock=self._clock)
        _log_dependency_start(logger=self._logger, dependency=dependency, keys=keys)
        try:
            runner = await self._execute_dependency_runner(
                dependency=dependency,
                keys=keys,
                runner_factory=runner_factory,
            )
        except TimeoutError:
            completed_at, duration_seconds = derive_completion_timestamp(
                started_at=started_at,
                started_monotonic=started_monotonic,
            )
            return self._result_service.build_timeout_result(
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
            return self._result_service.build_failed_result(
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
        return self._result_service.build_success_result(
            dependency=dependency,
            runner=runner,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

    async def _execute_dependency_runner(
        self,
        dependency: DependencyConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> ExecutionMetricsRunnerPort:
        """Execute dependency runner under timeout guard."""
        async with asyncio.timeout(dependency.timeout_seconds):
            runner = runner_factory(dependency.pipeline, keys)
            await runner.run()
        return runner
