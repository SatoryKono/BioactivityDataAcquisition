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


__all__ = ["EnrichmentCoordinator", "EnrichmentCoordinatorService"]


def _create_enricher_semaphore(max_concurrency: int) -> asyncio.Semaphore:
    """Build semaphore for enricher concurrency limiting."""
    return asyncio.Semaphore(max_concurrency)


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
        """Run all enrichers in parallel.

        Executes enrichers concurrently up to max_concurrency limit.
        Each enricher receives filtered keys based on its filter_condition.

        Args:
            keys: DataFrame with join keys from seed.
            enrichers: Enricher configurations.
            completed: Set of already-completed enrichers (for resume).
            runner_factory: Factory to create PipelineRunner for each enricher.

        Returns:
            Mapping of enricher name to result.

        Example:
            >>> results = await coordinator.run_enrichers(
            ...     keys=keys_df,
            ...     enrichers=[crossref_config, pubmed_config],
            ...     completed=frozenset(),
            ...     runner_factory=factory,
            ... )
            >>> results["crossref_publication"].is_success
            True
        """
        tasks = []
        enricher_names = []

        for enricher in enrichers:
            if enricher.pipeline in completed:
                self._logger.debug(
                    "Skipping completed enricher",
                    enricher=enricher.pipeline,
                )
                continue

            # Filter keys based on enricher condition
            filtered_keys = self._apply_filter(keys, enricher)

            if filtered_keys.is_empty():
                self._logger.info(
                    "Filter excluded all records for enricher",
                    enricher=enricher.pipeline,
                    filter_condition=enricher.filter_condition,
                )
                # Create skipped result synchronously
                tasks.append(asyncio.create_task(self._return_skipped(enricher)))
                enricher_names.append(enricher.pipeline)
                continue

            tasks.append(
                asyncio.create_task(
                    self._run_single_enricher(
                        enricher=enricher,
                        keys=filtered_keys,
                        runner_factory=runner_factory,
                    )
                )
            )
            enricher_names.append(enricher.pipeline)

        if not tasks:
            return {}

        self._logger.info(
            "Running enrichers",
            count=len(tasks),
            enrichers=enricher_names,
        )

        # Wait for all enrichers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        return self._process_results(enricher_names, results)

    def _apply_filter(
        self, keys: pl.DataFrame, enricher: EnricherConfig
    ) -> pl.DataFrame:
        """Apply filter condition to keys DataFrame.

        Filters keys based on the enricher's filter_condition.
        If no condition, returns all keys.

        Args:
            keys: Full keys DataFrame.
            enricher: Enricher configuration with optional filter.

        Returns:
            Filtered DataFrame.
        """
        import polars as pl

        if not enricher.filter_condition:
            return keys

        try:
            # Parse simple SQL-like conditions
            # Supports: "field IS NOT NULL", "field IS NULL"
            condition = enricher.filter_condition.strip()

            if " IS NOT NULL" in condition.upper():
                raw_field = condition.upper().replace(" IS NOT NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_not_null())

            if " IS NULL" in condition.upper():
                raw_field = condition.upper().replace(" IS NULL", "").strip()
                matched = self._find_column_case_insensitive(keys, raw_field)
                if matched:
                    return keys.filter(pl.col(matched).is_null())

            # For complex conditions, try SQL expression
            # This is a simplified implementation
            self._logger.warning(
                "Complex filter condition not fully supported",
                enricher=enricher.pipeline,
                condition=condition,
            )
            return keys

        except _FILTER_CONDITION_ERRORS as e:
            self._logger.warning(
                "Failed to apply filter condition",
                enricher=enricher.pipeline,
                condition=enricher.filter_condition,
                error=str(e),
                error_type=type(e).__name__,
            )
            return keys
        except BioETLError as e:
            self._logger.warning(
                "Failed to apply filter condition",
                enricher=enricher.pipeline,
                condition=enricher.filter_condition,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
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

            self._logger.info(
                "Starting enricher",
                enricher=enricher.pipeline,
                records_input=records_input,
                timeout_seconds=enricher.timeout_seconds,
            )

            try:
                # Apply timeout
                async with asyncio.timeout(enricher.timeout_seconds):
                    runner = runner_factory(enricher.pipeline, keys)
                    await runner.run()

                completed_at = datetime.now(tz=UTC)
                duration = (completed_at - started_at).total_seconds()

                # Extract stats from runner
                executor = getattr(runner, "_executor", None)
                records_enriched = 0
                records_errored = 0

                if executor:
                    records_enriched = getattr(executor, "records_silver", 0)
                    records_errored = getattr(executor, "records_quarantined", 0)

                # Calculate DQ error rate
                dq_error_rate = 0.0
                if records_input > 0:
                    dq_error_rate = records_errored / records_input

                # Check against thresholds
                hard_threshold = self._dq_config.get_enricher_hard_threshold(
                    enricher.pipeline
                )

                if dq_error_rate > hard_threshold:
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
                        error_message=f"DQ error rate {dq_error_rate:.2%} exceeds threshold {hard_threshold:.2%}",
                    )

                # Determine success vs partial
                status = EnrichmentStatus.SUCCESS
                if records_enriched < records_input:
                    status = EnrichmentStatus.PARTIAL

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
                    records_not_found=records_input
                    - records_enriched
                    - records_errored,
                    records_errored=records_errored,
                    dq_error_rate=dq_error_rate,
                    duration_seconds=duration,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            except TimeoutError:
                duration = (datetime.now(tz=UTC) - started_at).total_seconds()
                self._logger.warning(
                    "Enricher timed out",
                    enricher=enricher.pipeline,
                    timeout_seconds=enricher.timeout_seconds,
                )
                return EnrichmentResult.timeout(
                    enricher_name=enricher.pipeline,
                    timeout_seconds=enricher.timeout_seconds,
                    records_input=records_input,
                )

            except _ENRICHER_EXECUTION_ERRORS as e:
                duration = (datetime.now(tz=UTC) - started_at).total_seconds()

                # Re-raise for required enrichers (logged as error)
                if enricher.required:
                    self._logger.error(
                        "Required enricher failed",
                        enricher=enricher.pipeline,
                        error=str(e),
                        error_type=type(e).__name__,
                        required=True,
                    )
                    raise

                # Optional enricher failures are warnings (pipeline continues)
                self._logger.warning(
                    "Optional enricher failed",
                    enricher=enricher.pipeline,
                    error=str(e),
                    error_type=type(e).__name__,
                    required=False,
                )

                return EnrichmentResult.failed(
                    enricher_name=enricher.pipeline,
                    error_message=str(e),
                    records_input=records_input,
                    duration_seconds=duration,
                )
            except BioETLError as e:
                duration = (datetime.now(tz=UTC) - started_at).total_seconds()

                # Re-raise for required enrichers (logged as error)
                if enricher.required:
                    self._logger.error(
                        "Required enricher failed",
                        enricher=enricher.pipeline,
                        error=str(e),
                        error_type=type(e).__name__,
                        reason_code="unexpected_bioetl_error",
                        required=True,
                    )
                    raise

                # Optional enricher failures are warnings (pipeline continues)
                self._logger.warning(
                    "Optional enricher failed",
                    enricher=enricher.pipeline,
                    error=str(e),
                    error_type=type(e).__name__,
                    reason_code="unexpected_bioetl_error",
                    required=False,
                )

                return EnrichmentResult.failed(
                    enricher_name=enricher.pipeline,
                    error_message=str(e),
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


# Backward-compatible alias for iterative NAME-001 migration.
EnrichmentCoordinator = EnrichmentCoordinatorService
