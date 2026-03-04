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
        """Run all dependencies sequentially.

        Dependencies run after seed to have access to seed's keys for filtering.
        They populate Silver tables before enrichers run.

        Supports chained dependencies where key_source points to another
        dependency. In this case, keys are read from the source dependency's
        Silver table instead of using seed keys.

        Args:
            keys: DataFrame with join keys from seed.
            dependencies: Dependency configurations.
            completed: Set of already-completed dependencies (for resume).
            runner_factory: Factory to create PipelineRunner for each dependency.
            dependency_configs: All dependency configs for looking up key_source.

        Returns:
            Mapping of dependency name to result.

        Example:
            >>> results = await coordinator.run_dependencies(
            ...     keys=keys_df,
            ...     dependencies=[term_config],
            ...     completed=frozenset(),
            ...     runner_factory=factory,
            ... )
            >>> results["chembl_publication_term"].is_success
            True
        """
        results: dict[str, DependencyResult] = {}
        # Build lookup if not provided
        dep_config_lookup = dependency_configs or {d.pipeline: d for d in dependencies}

        if not dependencies:
            self._logger.debug(
                "No dependencies to run",
            )
            return results

        self._logger.info(
            "Running dependencies",
            count=len(dependencies),
            dependencies=[d.pipeline for d in dependencies],
        )

        for dependency in dependencies:
            if dependency.pipeline in completed:
                self._logger.debug(
                    "Skipping completed dependency",
                    dependency=dependency.pipeline,
                )
                results[dependency.pipeline] = DependencyResult.skipped(
                    pipeline_name=dependency.pipeline,
                    reason="Already completed (resumed from checkpoint)",
                )
                continue

            # Determine effective keys for this dependency
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

            # Stop on required dependency failure
            if dependency.required and not result.is_success:
                self._logger.error(
                    "Required dependency failed, stopping",
                    dependency=dependency.pipeline,
                    status=result.status.value,
                    error=result.error_message,
                )
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

        self._logger.info(
            "Starting dependency",
            dependency=dependency.pipeline,
            keys_count=len(keys),
            timeout_seconds=dependency.timeout_seconds,
        )

        try:
            # Apply timeout
            async with asyncio.timeout(dependency.timeout_seconds):
                runner = runner_factory(dependency.pipeline, keys)
                await runner.run()

            completed_at = datetime.now(tz=UTC)
            duration = (completed_at - started_at).total_seconds()

            # Extract stats from runner
            executor = getattr(runner, "_executor", None)
            records_extracted = 0
            records_silver = 0

            if executor:
                records_extracted = getattr(executor, "records_fetched", 0)
                records_silver = getattr(executor, "records_silver", 0)

            self._logger.info(
                "Dependency completed",
                dependency=dependency.pipeline,
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

        except TimeoutError:
            duration = (datetime.now(tz=UTC) - started_at).total_seconds()
            self._logger.warning(
                "Dependency timed out",
                dependency=dependency.pipeline,
                timeout_seconds=dependency.timeout_seconds,
            )
            return DependencyResult.timeout(
                pipeline_name=dependency.pipeline,
                timeout_seconds=dependency.timeout_seconds,
            )

        except _DEPENDENCY_EXECUTION_ERRORS as e:
            duration = (datetime.now(tz=UTC) - started_at).total_seconds()

            if dependency.required:
                self._logger.error(
                    "Required dependency failed",
                    dependency=dependency.pipeline,
                    error=str(e),
                    error_type=type(e).__name__,
                    required=True,
                )
            else:
                self._logger.warning(
                    "Optional dependency failed",
                    dependency=dependency.pipeline,
                    error=str(e),
                    error_type=type(e).__name__,
                    required=False,
                )

            return DependencyResult.failed(
                pipeline_name=dependency.pipeline,
                error_message=str(e),
                duration_seconds=duration,
            )
