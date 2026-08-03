"""Priority-order helpers for composite column ordering."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.column_priority_orderer import (
    collect_priority_field_columns,
    get_enricher_prefix,
    order_priority_columns,
)
from bioetl.domain.composite import EnricherConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class ColumnPriorityOrderingPolicy:
    """Explicit source-priority ordering helpers kept separate from the facade."""

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Return available source-priority columns for one composite field."""
        columns, used_parse_fallback = collect_priority_field_columns(
            field=field,
            enrichers=enrichers,
            available_columns=available_columns,
            seed_pipeline=seed_pipeline,
        )
        if used_parse_fallback and seed_pipeline:
            self._logger.debug(
                "Could not parse seed pipeline for field collection",
                seed_pipeline=seed_pipeline,
                field=field,
            )
        return columns

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Sort compatible columns according to configured source priorities."""
        ordered_cols, used_parse_fallback = order_priority_columns(
            field=field,
            columns=columns,
            priorities=priorities,
            seed_pipeline=seed_pipeline,
        )
        if used_parse_fallback and seed_pipeline:
            self._logger.debug(
                "Could not parse seed pipeline for priority ordering",
                seed_pipeline=seed_pipeline,
                field=field,
            )
        return ordered_cols

    def filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
        can_coalesce: Callable[[pl.DataFrame, str, str], bool],
    ) -> tuple[list[str], list[str]]:
        """Split ordered columns into coalescible and incompatible groups."""
        if not ordered_cols:
            return [], []

        base_col = ordered_cols[0]
        compatible_cols = [base_col]
        incompatible_cols: list[str] = []

        for col in ordered_cols[1:]:
            if can_coalesce(df, base_col, col):
                compatible_cols.append(col)
                continue
            self._logger.debug(
                "Skipping column with incompatible type in explicit rules",
                field=field,
                incompatible_col=col,
                base_type=str(df[base_col].dtype),
                col_type=str(df[col].dtype),
            )
            incompatible_cols.append(col)

        return compatible_cols, incompatible_cols

    @staticmethod
    def get_enricher_prefix(enricher_pipeline: str) -> str:
        """Expose legacy prefix helper for compatibility call sites."""
        return get_enricher_prefix(enricher_pipeline)


__all__ = ["ColumnPriorityOrderingPolicy"]
