"""Dependency Coordinator.

Application Service that coordinates dependency pipeline execution.
Dependencies run after the seed but before enrichers to populate
Silver tables that enrichers will read from.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import DependencyResult

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import DependencyConfig
    from bioetl.domain.ports import LoggerPort


class DependencyCoordinator:
    """Coordinates dependency pipeline execution.

    Dependencies run sequentially after the seed but before enrichers.
    They populate Silver tables that enrichers will read from.

    Unlike enrichers which run in parallel, dependencies run sequentially
    to avoid overwhelming APIs and ensure predictable ordering.

    Attributes:
        logger: Structured logger.

    Example:
        >>> coordinator = DependencyCoordinator(logger=logger)
        >>> results = await coordinator.run_dependencies(
        ...     keys=keys_df,
        ...     dependencies=dependency_configs,
        ...     completed=frozenset(),
        ...     runner_factory=factory,
        ... )
    """

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize dependency coordinator.

        Args:
            logger: Structured logger.
        """
        self._logger = logger

    async def run_dependencies(
        self,
        keys: pl.DataFrame,
        dependencies: Sequence[DependencyConfig],
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> dict[str, DependencyResult]:
        """Run all dependencies sequentially.

        Dependencies run after seed to have access to seed's keys for filtering.
        They populate Silver tables before enrichers run.

        Args:
            keys: DataFrame with join keys from seed.
            dependencies: Dependency configurations.
            completed: Set of already-completed dependencies (for resume).
            runner_factory: Factory to create PipelineRunner for each dependency.

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

            result = await self._run_single_dependency(
                dependency=dependency,
                keys=keys,
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

        except Exception as e:
            duration = (datetime.now(tz=UTC) - started_at).total_seconds()

            if dependency.required:
                self._logger.error(
                    "Required dependency failed",
                    dependency=dependency.pipeline,
                    error=str(e),
                    required=True,
                )
            else:
                self._logger.warning(
                    "Optional dependency failed",
                    dependency=dependency.pipeline,
                    error=str(e),
                    required=False,
                )

            return DependencyResult.failed(
                pipeline_name=dependency.pipeline,
                error_message=str(e),
                duration_seconds=duration,
            )
