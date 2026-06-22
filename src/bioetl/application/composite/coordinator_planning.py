"""Task-planning helpers for enrichment coordinator orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import ExecutionMetricsRunnerPort, LoggerPort

__all__ = [
    "PlannedEnricherTask",
    "apply_enricher_filter",
    "build_enricher_tasks",
    "find_column_case_insensitive",
]


@dataclass(frozen=True, slots=True)
class PlannedEnricherTask:
    """Concrete task planned for one enricher pipeline."""

    pipeline: str
    task: asyncio.Task[EnrichmentResult]


class _CoordinatorPlanningHost(Protocol):
    """Minimal coordinator host contract required for task planning."""

    _logger: LoggerPort

    def _apply_filter(
        self,
        keys: pl.DataFrame,
        enricher: EnricherConfig,
    ) -> pl.DataFrame: ...

    async def _return_skipped(self, enricher: EnricherConfig) -> EnrichmentResult: ...

    async def _run_single_enricher(
        self,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
        runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    ) -> EnrichmentResult: ...


def find_column_case_insensitive(df: pl.DataFrame, column: str) -> str | None:
    """Resolve a column name using case-insensitive matching."""
    column_lower = column.lower()
    for col_name in df.columns:
        resolved_name = str(col_name)
        if resolved_name.lower() == column_lower:
            return resolved_name
    return None


def apply_enricher_filter(
    *,
    logger: LoggerPort,
    keys: pl.DataFrame,
    enricher: EnricherConfig,
    find_column: Callable[[pl.DataFrame, str], str | None],
    filter_errors: tuple[type[BaseException], ...],
) -> pl.DataFrame:
    """Apply supported NULL/NOT NULL filter conditions to enricher keys."""
    if not enricher.filter_condition:
        return keys

    try:
        condition = enricher.filter_condition.strip()
        condition_upper = condition.upper()

        if " IS NOT NULL" in condition_upper:
            raw_field = condition_upper.replace(" IS NOT NULL", "").strip()
            matched = find_column(keys, raw_field)
            if matched:
                return keys.filter(pl.col(matched).is_not_null())

        if " IS NULL" in condition_upper:
            raw_field = condition_upper.replace(" IS NULL", "").strip()
            matched = find_column(keys, raw_field)
            if matched:
                return keys.filter(pl.col(matched).is_null())

        logger.warning(
            "Complex filter condition not fully supported",
            enricher=enricher.pipeline,
            condition=condition,
        )
        return keys
    except filter_errors as error:
        logger.warning(
            "Failed to apply filter condition",
            enricher=enricher.pipeline,
            condition=enricher.filter_condition,
            error=str(error),
            error_type=type(error).__name__,
            reason_code=(
                "unexpected_bioetl_error" if isinstance(error, BioETLError) else None
            ),
        )
        return keys


def _build_enricher_task(
    service: _CoordinatorPlanningHost,
    *,
    keys: pl.DataFrame,
    enricher: EnricherConfig,
    completed: frozenset[str],
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> PlannedEnricherTask | None:
    """Plan one enricher task or skip it when already complete/excluded."""
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
        return PlannedEnricherTask(
            pipeline=enricher.pipeline,
            task=asyncio.create_task(service._return_skipped(enricher)),
        )

    return PlannedEnricherTask(
        pipeline=enricher.pipeline,
        task=asyncio.create_task(
            service._run_single_enricher(
                enricher=enricher,
                keys=filtered_keys,
                runner_factory=runner_factory,
            )
        ),
    )


def build_enricher_tasks(
    service: _CoordinatorPlanningHost,
    *,
    keys: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    completed: frozenset[str],
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
) -> list[PlannedEnricherTask]:
    """Plan the full enricher task set before execution policy runs."""
    return [
        planned_task
        for enricher in enrichers
        if (
            planned_task := _build_enricher_task(
                service,
                keys=keys,
                enricher=enricher,
                completed=completed,
                runner_factory=runner_factory,
            )
        )
        is not None
    ]
