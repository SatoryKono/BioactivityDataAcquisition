"""Enrichment Coordinator.

Provides ``EnrichmentCoordinatorService``, which fans out enricher pipelines
concurrently using ``asyncio.gather`` bounded by a configurable semaphore.
Each enricher receives a filtered subset of seed keys and runs independently;
results are collected into typed ``EnrichmentResult`` objects regardless of
whether the enricher succeeded, timed out, was skipped by filter, or failed.

**Fail-fast semantics (RF-007.1):** When a *required* enricher fails or times
out, the exception propagates immediately through ``asyncio.gather`` (no
``return_exceptions``), cancelling all remaining sibling tasks. Optional
enricher errors are caught internally and returned as ``FAILED`` results.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence

import polars as pl

from bioetl.application.composite.coordinator_planning import (
    apply_enricher_filter,
    build_enricher_tasks,
    find_column_case_insensitive,
)
from bioetl.application.composite.coordinator_result_mixin import (
    EnrichmentCoordinatorResultMixin,
)
from bioetl.application.composite.helpers.coordinator_execution import (
    complete_enricher_execution,
    handle_enricher_execution_error,
    handle_enricher_timeout,
    run_enricher_with_timeout,
    start_enricher_execution,
)
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.composite import CompositeDQConfig, EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort

_FILTER_CONDITION_ERRORS = (
    ValueError,
    TypeError,
    RuntimeError,
)
_ENRICHER_EXECUTION_ERRORS = (
    NetworkError,
    StorageError,
    CheckpointConflictError,
    DataQualityError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
)

__all__ = ["EnrichmentCoordinatorService"]


class EnrichmentCoordinatorService(EnrichmentCoordinatorResultMixin):
    """Coordinates parallel enrichment pipeline execution."""

    def __init__(
        self,
        logger: LoggerPort,
        dq_config: CompositeDQConfig,
        max_concurrency: int = 4,
        semaphore_factory: Callable[[int], asyncio.Semaphore] | None = None,
        clock: ClockPort | None = None,
    ) -> None:
        """Initialize enrichment coordinator.

        Args:
            logger: Structured logger for per-enricher progress, skip, and
                error events.
            dq_config: Composite data-quality configuration that governs
                DQ thresholds applied to enricher outputs.
            max_concurrency: Maximum number of enricher pipelines that may
                run simultaneously; defaults to 4. Controls the semaphore
                capacity used to throttle ``asyncio`` tasks.
            semaphore_factory: Optional callable that creates the concurrency
                semaphore from ``max_concurrency``; defaults to
                ``asyncio.Semaphore``. Inject a custom factory in tests to
                control scheduling behaviour.
        """
        self._logger = logger
        self._dq_config = dq_config
        self._max_concurrency = max_concurrency
        self._semaphore_factory = semaphore_factory or asyncio.Semaphore
        self._semaphore = self._semaphore_factory(max_concurrency)
        self._clock = resolve_runtime_clock(clock)

    async def run_enrichers(
        self,
        keys: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> dict[str, EnrichmentResult]:
        """Run all enrichers concurrently and collect typed enrichment results.

        Args:
            keys: DataFrame of seed keys to pass to each enricher pipeline.
            enrichers: Enricher configurations to execute.
            completed: Set of pipeline names already completed (skipped when resuming).
            runner_factory: Callable that creates a metrics-readable runner for a
                given pipeline name and key DataFrame.

        Returns:
            Mapping from enricher pipeline name to its EnrichmentResult, including
            skipped, failed, partial, and successful outcomes.
        """
        planned_tasks = build_enricher_tasks(
            self,
            keys=keys,
            enrichers=enrichers,
            completed=completed,
            runner_factory=runner_factory,
        )
        if not planned_tasks:
            return {}

        enricher_names = [planned_task.pipeline for planned_task in planned_tasks]
        tasks = [planned_task.task for planned_task in planned_tasks]
        self._logger.info(
            "Running enrichers",
            count=len(tasks),
            enrichers=enricher_names,
        )
        results = await asyncio.gather(*tasks)
        return self._process_results(enricher_names, results)

    def _apply_filter(
        self, keys: pl.DataFrame, enricher: EnricherConfig
    ) -> pl.DataFrame:
        """Apply simple NULL/NOT NULL filter condition for enricher keys."""
        return apply_enricher_filter(
            logger=self._logger,
            keys=keys,
            enricher=enricher,
            find_column=self._find_column_case_insensitive,
            filter_errors=(*_FILTER_CONDITION_ERRORS, BioETLError),
        )

    def _find_column_case_insensitive(
        self, df: pl.DataFrame, column: str
    ) -> str | None:
        """Find column name with case-insensitive matching."""
        return find_column_case_insensitive(df, column)

    async def _return_skipped(self, enricher: EnricherConfig) -> EnrichmentResult:
        """Return a skipped result for an enricher."""
        await asyncio.sleep(0)
        return EnrichmentResult.skipped(
            enricher_name=enricher.pipeline,
            reason=f"Filter condition excluded all records: {enricher.filter_condition}",
        )

    async def _run_single_enricher(
        self,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> EnrichmentResult:
        """Run a single enricher with timeout and error handling."""
        async with self._semaphore:
            execution_context = start_enricher_execution(self, enricher, keys)

            try:
                runner, completed_at, duration = await run_enricher_with_timeout(
                    enricher=enricher,
                    keys=keys,
                    runner_factory=runner_factory,
                    started_at=execution_context.started_at,
                    started_monotonic_at=execution_context.started_monotonic_at,
                )
                return complete_enricher_execution(
                    self,
                    execution_context=execution_context,
                    runner=runner,
                    completed_at=completed_at,
                    duration=duration,
                )
            except TimeoutError:
                return handle_enricher_timeout(self, execution_context)
            except _ENRICHER_EXECUTION_ERRORS as e:
                return handle_enricher_execution_error(
                    self,
                    e,
                    execution_context=execution_context,
                )
            except BioETLError as e:
                return handle_enricher_execution_error(
                    self,
                    e,
                    execution_context=execution_context,
                    reason_code="unexpected_bioetl_error",
                )
