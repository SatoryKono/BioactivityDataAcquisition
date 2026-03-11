"""Enrichment Coordinator."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.coordinator_result_mixin import (
    EnrichmentCoordinatorResultMixin,
)
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import CompositeDQConfig, EnricherConfig
    from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort

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


def _create_enricher_semaphore(max_concurrency: int) -> asyncio.Semaphore:
    """Build semaphore for enricher concurrency limiting."""
    return asyncio.Semaphore(max_concurrency)


def _build_enricher_task(
    service: EnrichmentCoordinatorService,
    *,
    keys: pl.DataFrame,
    enricher: EnricherConfig,
    completed: frozenset[str],
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> tuple[str, asyncio.Task[EnrichmentResult]] | None:
    """Build async task for one enricher or return None when skipped."""
    if enricher.pipeline in completed:
        service._logger.debug(
            "Skipping completed enricher",
            enricher=enricher.pipeline,
        )
        return None

    filtered_keys = service._apply_filter(keys, enricher)
    if filtered_keys.is_empty():
        service._logger.info(
            "Filter excluded all records for enricher",
            enricher=enricher.pipeline,
            filter_condition=enricher.filter_condition,
        )
        return (
            enricher.pipeline,
            asyncio.create_task(service._return_skipped(enricher)),
        )

    return (
        enricher.pipeline,
        asyncio.create_task(
            service._run_single_enricher(
                enricher=enricher,
                keys=filtered_keys,
                runner_factory=runner_factory,
            )
        ),
    )


class EnrichmentCoordinatorService(EnrichmentCoordinatorResultMixin):
    """Coordinates parallel enrichment pipeline execution."""

    def __init__(
        self,
        logger: LoggerPort,
        dq_config: CompositeDQConfig,
        max_concurrency: int = 4,
        semaphore_factory: Callable[[int], asyncio.Semaphore] | None = None,
    ) -> None:
        """Initialize enrichment coordinator."""
        self._logger = logger
        self._dq_config = dq_config
        self._max_concurrency = max_concurrency
        self._semaphore_factory = semaphore_factory or _create_enricher_semaphore
        self._semaphore = self._semaphore_factory(max_concurrency)

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
        task_specs = [
            task_spec
            for enricher in enrichers
            if (
                task_spec := _build_enricher_task(
                    self,
                    keys=keys,
                    enricher=enricher,
                    completed=completed,
                    runner_factory=runner_factory,
                )
            )
            is not None
        ]
        if not task_specs:
            return {}

        enricher_names = [name for name, _ in task_specs]
        tasks = [task for _, task in task_specs]
        self._logger.info(
            "Running enrichers",
            count=len(tasks),
            enrichers=enricher_names,
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_results(enricher_names, results)

    def _apply_filter(
        self, keys: pl.DataFrame, enricher: EnricherConfig
    ) -> pl.DataFrame:
        """Apply simple NULL/NOT NULL filter condition for enricher keys."""
        import polars as pl

        if not enricher.filter_condition:
            return keys

        try:
            condition = enricher.filter_condition.strip()
            condition_upper = condition.upper()

            if " IS NOT NULL" in condition_upper:
                raw_field = condition_upper.replace(" IS NOT NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_not_null())

            if " IS NULL" in condition_upper:
                raw_field = condition_upper.replace(" IS NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_null())

            self._logger.warning(
                "Complex filter condition not fully supported",
                enricher=enricher.pipeline,
                condition=condition,
            )
            return keys

        except (*_FILTER_CONDITION_ERRORS, BioETLError) as e:
            self._logger.warning(
                "Failed to apply filter condition",
                enricher=enricher.pipeline,
                condition=enricher.filter_condition,
                error=str(e),
                error_type=type(e).__name__,
                reason_code=(
                    "unexpected_bioetl_error" if isinstance(e, BioETLError) else None
                ),
            )
            return keys

    def _find_column_case_insensitive(
        self, df: pl.DataFrame, column: str
    ) -> str | None:
        """Find column name with case-insensitive matching."""
        column_lower = column.lower()
        col_name: str
        for col_name in df.columns:
            if col_name.lower() == column_lower:
                return col_name
        return None

    async def _return_skipped(self, enricher: EnricherConfig) -> EnrichmentResult:
        """Return a skipped result for an enricher."""
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
            started_at = datetime.now(tz=UTC)
            records_input = len(keys)
            self._log_enricher_start(enricher, records_input)

            try:
                runner, completed_at, duration = await self._run_with_timeout(
                    enricher=enricher,
                    keys=keys,
                    runner_factory=runner_factory,
                    started_at=started_at,
                )
                return self._build_enricher_result(
                    enricher=enricher,
                    runner=runner,
                    records_input=records_input,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration=duration,
                )
            except TimeoutError:
                return self._build_timeout_result(enricher, records_input, started_at)
            except _ENRICHER_EXECUTION_ERRORS as e:
                return self._handle_enricher_error(
                    e,
                    enricher,
                    records_input,
                    started_at,
                )
            except BioETLError as e:
                return self._handle_enricher_error(
                    e,
                    enricher,
                    records_input,
                    started_at,
                    reason_code="unexpected_bioetl_error",
                )

    def _log_enricher_start(self, enricher: EnricherConfig, records_input: int) -> None:
        self._logger.info(
            "Starting enricher",
            enricher=enricher.pipeline,
            records_input=records_input,
            timeout_seconds=enricher.timeout_seconds,
        )

    async def _run_with_timeout(
        self,
        *,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
        started_at: datetime,
    ) -> tuple[ExecutionMetricsRunnerPort, datetime, float]:
        async with asyncio.timeout(enricher.timeout_seconds):
            runner = runner_factory(enricher.pipeline, keys)
            await runner.run()
        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()
        return runner, completed_at, duration
