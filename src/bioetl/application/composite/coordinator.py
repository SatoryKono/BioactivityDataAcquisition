"""Enrichment Coordinator.

Application Service that coordinates parallel enrichment pipeline execution.
Implements fan-out pattern with async gather for concurrent enrichers.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.composite.config import CompositeDQConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict

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
    runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
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


class EnrichmentCoordinatorService:
    """Coordinates parallel enrichment pipeline execution.

    Implements fan-out pattern with async gather for concurrent enrichers.
    Handles timeouts, failures, and partial completion.

    This service is responsible for:
    - Filtering keys based on enricher conditions
    - Running enrichers in parallel (up to max_concurrency)
    - Handling per-enricher timeouts
    - Aggregating results

    Attributes:
        logger: Structured logger.
        dq_config: DQ thresholds for enricher evaluation.
        max_concurrency: Maximum concurrent enrichers.

    Example:
        >>> coordinator = EnrichmentCoordinator(
        ...     logger=logger,
        ...     dq_config=dq_config,
        ...     max_concurrency=4,
        ... )
        >>> results = await coordinator.run_enrichers(
        ...     keys=keys_df,
        ...     enrichers=enricher_configs,
        ...     runner_factory=factory,
        ... )
    """

    def __init__(
        self,
        logger: LoggerPort,
        dq_config: CompositeDQConfig,
        max_concurrency: int = 4,
        semaphore_factory: Callable[[int], asyncio.Semaphore] | None = None,
    ) -> None:
        """Initialize enrichment coordinator.

        Args:
            logger: Structured logger.
            dq_config: DQ thresholds configuration.
            max_concurrency: Maximum concurrent enrichers.
            semaphore_factory: Optional factory for semaphore creation.
        """
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
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> dict[str, EnrichmentResult]:
        """Run all enrichers concurrently and collect typed enrichment results."""
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
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
    ) -> EnrichmentResult:
        """Run a single enricher with timeout and error handling.

        Uses semaphore to limit concurrency and handles:
        - Timeout per enricher
        - Critical errors (re-raised for required enrichers)
        - Recoverable errors (logged, returned as failed)

        Args:
            enricher: Enricher configuration.
            keys: Filtered keys DataFrame.
            runner_factory: Factory to create PipelineRunner.

        Returns:
            EnrichmentResult with execution outcome.
        """
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
        runner_factory: Callable[[str, pl.DataFrame], PipelineRunner],
        started_at: datetime,
    ) -> tuple[PipelineRunner, datetime, float]:
        async with asyncio.timeout(enricher.timeout_seconds):
            runner = runner_factory(enricher.pipeline, keys)
            await runner.run()
        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()
        return runner, completed_at, duration

    def _build_enricher_result(
        self,
        *,
        enricher: EnricherConfig,
        runner: PipelineRunner,
        records_input: int,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult:
        records_enriched, records_errored, dq_error_rate = self._extract_runner_stats(
            runner, records_input
        )
        hard_threshold = self._dq_config.get_enricher_hard_threshold(enricher.pipeline)
        if dq_error_rate > hard_threshold:
            return self._build_threshold_failure_result(
                enricher=enricher,
                records_input=records_input,
                records_enriched=records_enriched,
                records_errored=records_errored,
                dq_error_rate=dq_error_rate,
                hard_threshold=hard_threshold,
                started_at=started_at,
                completed_at=completed_at,
                duration=duration,
            )

        status = (
            EnrichmentStatus.PARTIAL
            if records_enriched < records_input
            else EnrichmentStatus.SUCCESS
        )
        self._logger.info(
            "Enricher completed",
            enricher=enricher.pipeline,
            status=status.value,
            records_enriched=records_enriched,
            duration_seconds=duration,
        )
        return EnrichmentResult(
            enricher_name=enricher.pipeline,
            status=status,
            records_input=records_input,
            records_enriched=records_enriched,
            records_not_found=records_input - records_enriched - records_errored,
            records_errored=records_errored,
            dq_error_rate=dq_error_rate,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _build_threshold_failure_result(
        self,
        *,
        enricher: EnricherConfig,
        records_input: int,
        records_enriched: int,
        records_errored: int,
        dq_error_rate: float,
        hard_threshold: float,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult:
        self._logger.warning(
            "Enricher exceeded hard DQ threshold",
            enricher=enricher.pipeline,
            dq_error_rate=dq_error_rate,
            threshold=hard_threshold,
        )
        return EnrichmentResult(
            enricher_name=enricher.pipeline,
            status=EnrichmentStatus.FAILED,
            records_input=records_input,
            records_enriched=records_enriched,
            records_errored=records_errored,
            dq_error_rate=dq_error_rate,
            duration_seconds=duration,
            started_at=started_at,
            completed_at=completed_at,
            error_message=(
                f"DQ error rate {dq_error_rate:.2%} "
                f"exceeds threshold {hard_threshold:.2%}"
            ),
        )

    def _build_timeout_result(
        self,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
    ) -> EnrichmentResult:
        duration = (datetime.now(tz=UTC) - started_at).total_seconds()
        self._logger.warning(
            "Enricher timed out",
            enricher=enricher.pipeline,
            timeout_seconds=enricher.timeout_seconds,
            duration_seconds=duration,
        )
        return EnrichmentResult.timeout(
            enricher_name=enricher.pipeline,
            timeout_seconds=enricher.timeout_seconds,
            records_input=records_input,
        )

    @staticmethod
    def _extract_runner_stats(
        runner: PipelineRunner,
        records_input: int,
    ) -> tuple[int, int, float]:
        """Extract enrichment stats from runner executor."""
        executor = getattr(runner, "_executor", None)
        records_enriched = getattr(executor, "records_silver", 0) if executor else 0
        records_errored = getattr(executor, "records_quarantined", 0) if executor else 0
        dq_error_rate = records_errored / records_input if records_input > 0 else 0.0
        return records_enriched, records_errored, dq_error_rate

    def _handle_enricher_error(
        self,
        error: Exception,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
        *,
        reason_code: str | None = None,
    ) -> EnrichmentResult:
        """Handle enricher execution error.

        Required enrichers: log as error and re-raise.
        Optional enrichers: log as warning and return failed result.
        """
        duration = (datetime.now(tz=UTC) - started_at).total_seconds()
        log_kwargs: JsonDict = {
            "enricher": enricher.pipeline,
            "error": str(error),
            "error_type": type(error).__name__,
            "required": enricher.required,
        }
        if reason_code:
            log_kwargs["reason_code"] = reason_code

        if enricher.required:
            self._logger.error("Required enricher failed", **log_kwargs)
            raise

        self._logger.warning("Optional enricher failed", **log_kwargs)
        return EnrichmentResult.failed(
            enricher_name=enricher.pipeline,
            error_message=str(error),
            records_input=records_input,
            duration_seconds=duration,
        )

    def _process_results(
        self,
        enricher_names: list[str],
        results: list[EnrichmentResult | BaseException],
    ) -> dict[str, EnrichmentResult]:
        """Process gathered results, handling exceptions.

        Converts exceptions to failed results for optional enrichers.
        Re-raises exceptions for required enrichers (should not happen
        as they're raised in _run_single_enricher).

        Args:
            enricher_names: Names of enrichers in order.
            results: Results from asyncio.gather.

        Returns:
            Mapping of enricher name to result.
        """
        processed: dict[str, EnrichmentResult] = {}

        for name, result in zip(enricher_names, results, strict=True):
            if isinstance(result, BaseException):
                # Should not happen for required (already re-raised)
                processed[name] = EnrichmentResult.failed(
                    enricher_name=name,
                    error_message=str(result),
                )
            else:
                processed[name] = result

        return processed
