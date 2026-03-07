"""Dependency coordination for seed->dependency key propagation (ADR-026)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.dependency_key_resolvers import (
    ChainedKeyResolver,
    SeedKeyResolver,
    create_chained_key_resolver,
    create_seed_key_resolver,
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
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import DependencyConfig
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


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


def _duration_seconds(started_at: datetime, completed_at: datetime) -> float:
    """Calculate wall-clock duration in seconds."""
    return (completed_at - started_at).total_seconds()


def _extract_runner_metrics(runner: PipelineRunner) -> tuple[int, int]:
    """Extract available row counters from runner executor."""
    executor = getattr(runner, "_executor", None)
    if executor is None:
        return 0, 0
    return (
        getattr(executor, "records_fetched", 0),
        getattr(executor, "records_silver", 0),
    )


def _build_dependency_lookup(
    *,
    dependencies: Sequence[DependencyConfig],
    dependency_configs: dict[str, DependencyConfig] | None,
) -> dict[str, DependencyConfig]:
    """Build dependency lookup map with optional explicit override."""
    if dependency_configs is not None:
        return dependency_configs
    return {dependency.pipeline: dependency for dependency in dependencies}


def _build_completed_skip_result(*, dependency: DependencyConfig) -> DependencyResult:
    """Build skipped result payload for already completed dependencies."""
    return DependencyResult.skipped(
        pipeline_name=dependency.pipeline,
        reason="Already completed (resumed from checkpoint)",
    )


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


def _should_stop_after_result(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    result: DependencyResult,
) -> bool:
    """Return True when required dependency failure must stop execution."""
    if not dependency.required or result.is_success:
        return False
    logger.error(
        "Required dependency failed, stopping",
        dependency=dependency.pipeline,
        status=result.status.value,
        error=result.error_message,
    )
    return True


def _maybe_mark_completed_dependency(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    completed: frozenset[str],
    results: dict[str, DependencyResult],
) -> bool:
    """Store skipped result for completed dependency and return handled flag."""
    if dependency.pipeline not in completed:
        return False
    logger.debug(
        "Skipping completed dependency",
        dependency=dependency.pipeline,
    )
    results[dependency.pipeline] = _build_completed_skip_result(
        dependency=dependency,
    )
    return True


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


def _log_dependency_success(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    records_extracted: int,
    records_silver: int,
    duration_seconds: float,
) -> None:
    """Emit structured log entry for dependency success."""
    logger.info(
        "Dependency completed",
        dependency=dependency.pipeline,
        records_extracted=records_extracted,
        records_silver=records_silver,
        duration_seconds=duration_seconds,
    )


def _build_timeout_result(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    started_at: datetime,
) -> DependencyResult:
    """Build timeout result and emit warning log."""
    logger.warning(
        "Dependency timed out",
        dependency=dependency.pipeline,
        timeout_seconds=dependency.timeout_seconds,
        duration_seconds=_duration_seconds(
            started_at=started_at,
            completed_at=datetime.now(tz=UTC),
        ),
    )
    return DependencyResult.timeout(
        pipeline_name=dependency.pipeline,
        timeout_seconds=dependency.timeout_seconds,
    )


def _build_failed_result(
    *,
    logger: LoggerPort,
    dependency: DependencyConfig,
    error: Exception,
    started_at: datetime,
) -> DependencyResult:
    """Build failed result and emit required/optional failure log."""
    duration = _duration_seconds(
        started_at=started_at,
        completed_at=datetime.now(tz=UTC),
    )
    log_method = logger.error if dependency.required else logger.warning
    log_method(
        "Required dependency failed"
        if dependency.required
        else "Optional dependency failed",
        dependency=dependency.pipeline,
        error=str(error),
        error_type=type(error).__name__,
        required=dependency.required,
        duration_seconds=duration,
    )
    return DependencyResult.failed(
        pipeline_name=dependency.pipeline,
        error_message=str(error),
        duration_seconds=duration,
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
        delta_reader: Reader for Silver tables (for chained dependencies).

    Example:
        >>> coordinator = DependencyCoordinator(logger=logger, delta_reader=reader)
        >>> results = await coordinator.run_dependencies(
        ...     keys=keys_df,
        ...     dependencies=dependency_configs,
        ...     completed=frozenset(),
        ...     runner_factory=factory,
        ... )
    """

    def __init__(
        self,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        seed_key_resolver: SeedKeyResolver | None = None,
        chained_key_resolver: ChainedKeyResolver | None = None,
    ) -> None:
        """Initialize dependency coordinator.

        Args:
            logger: Structured logger.
            delta_reader: Reader for Silver tables (required for chained dependencies).
            seed_key_resolver: Optional custom resolver for seed-key dependencies.
            chained_key_resolver: Optional custom resolver for chained dependencies.
        """
        self._logger = logger
        self._delta_reader = delta_reader
        self._seed_key_resolver = seed_key_resolver or create_seed_key_resolver(logger)
        self._chained_key_resolver = chained_key_resolver or (
            create_chained_key_resolver(logger)
        )

    async def run_dependencies(
        self,
        keys: pl.DataFrame,
        dependencies: Sequence[DependencyConfig],
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
        dependency_configs: dict[str, DependencyConfig] | None = None,
    ) -> dict[str, DependencyResult]:
        """Run dependencies sequentially and return per-pipeline results.

        Uses seed keys for standard dependencies and source-table keys for
        chained dependencies (`key_source`). Stops early when a required
        dependency fails.

        Args:
            keys: DataFrame of seed keys passed to each dependency pipeline.
            dependencies: Ordered sequence of dependency configurations to execute.
            completed: Set of pipeline names already completed (skipped when resuming).
            runner_factory: Callable that creates a PipelineRunner given a pipeline name
                and key DataFrame.
            dependency_configs: Optional full config mapping for resolving chained keys.

        Returns:
            Mapping from dependency pipeline name to its DependencyResult.
        """
        results: dict[str, DependencyResult] = {}
        dep_config_lookup = _build_dependency_lookup(
            dependencies=dependencies,
            dependency_configs=dependency_configs,
        )

        if not dependencies:
            self._logger.debug(
                "No dependencies to run",
            )
            return results

        _log_dependencies_batch_start(logger=self._logger, dependencies=dependencies)

        for dependency in dependencies:
            if _maybe_mark_completed_dependency(
                logger=self._logger,
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

            if _should_stop_after_result(
                logger=self._logger,
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
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> DependencyResult:
        """Run a single dependency with timeout and error handling.

        Args:
            dependency: Dependency configuration.
            keys: Keys DataFrame from seed.
            runner_factory: Factory to create PipelineRunner.

        Returns:
            DependencyResult with execution outcome.
        """
        started_at = datetime.now(tz=UTC)
        _log_dependency_start(logger=self._logger, dependency=dependency, keys=keys)
        try:
            runner = await self._execute_dependency_runner(
                dependency=dependency,
                keys=keys,
                runner_factory=runner_factory,
            )
        except TimeoutError:
            return _build_timeout_result(
                logger=self._logger,
                dependency=dependency,
                started_at=started_at,
            )
        except _DEPENDENCY_EXECUTION_ERRORS as e:
            return _build_failed_result(
                logger=self._logger,
                dependency=dependency,
                error=e,
                started_at=started_at,
            )

        completed_at = datetime.now(tz=UTC)
        duration = _duration_seconds(started_at=started_at, completed_at=completed_at)
        records_extracted, records_silver = _extract_runner_metrics(runner)
        _log_dependency_success(
            logger=self._logger,
            dependency=dependency,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration,
        )
        return DependencyResult.success(
            pipeline_name=dependency.pipeline,
            records_extracted=records_extracted,
            records_silver=records_silver,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _execute_dependency_runner(
        self,
        dependency: DependencyConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> PipelineRunner:
        """Execute dependency runner under timeout guard."""
        async with asyncio.timeout(dependency.timeout_seconds):
            runner = runner_factory(dependency.pipeline, keys)
            await runner.run()
        return runner
