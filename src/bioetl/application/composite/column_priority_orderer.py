"""Column priority ordering helpers for composite conflict resolution."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import polars as pl

from bioetl.application.composite.column_priority_orderer_helpers import (
    collect_field_columns as collect_priority_field_columns,
)
from bioetl.application.composite.column_priority_orderer_helpers import (
    get_enricher_prefix as get_priority_enricher_prefix,
)
from bioetl.application.composite.column_priority_orderer_helpers import (
    order_columns_by_priority as order_priority_columns,
)
from bioetl.application.composite.column_priority_orderer_helpers import (
    resolve_priority_column as resolve_priority_column_helper,
)
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite.config import EnricherConfig
from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnPriorityOrderer"]


class ColumnPriorityOrderer:
    """Resolves source column ordering for explicit field priority rules."""

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Collect all qualified/legacy columns for a field from all sources.

        Args:
            field: Unqualified field name to look up across sources.
            enrichers: Enricher configurations whose pipelines are searched.
            available_columns: Set of column names present in the current DataFrame.
            seed_pipeline: Optional seed pipeline name used to generate the seed column.

        Returns:
            List of qualified column names (e.g. ``provider.entity.field``) present in
            the DataFrame for the given field across seed and all enrichers.
        """
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
        """Order columns by configured source priority.

        Args:
            field: Unqualified field name used for column resolution.
            columns: List of qualified column names to reorder.
            priorities: Ordered sequence of source names (e.g. ``["seed", "chembl"]``).
            seed_pipeline: Optional seed pipeline name used to resolve the ``"seed"`` token.

        Returns:
            List of column names reordered so that highest-priority sources appear first,
            with any unmatched columns appended at the end.
        """
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
        """Filter columns to those compatible for coalescing.

        Args:
            df: DataFrame containing the columns to evaluate.
            field: Unqualified field name used for log context.
            ordered_cols: Priority-ordered list of column names to check.
            can_coalesce: Callable that returns True when two columns are type-compatible.

        Returns:
            Tuple of (compatible_cols, incompatible_cols) where compatible_cols are
            type-compatible with the leading column and incompatible_cols are not.
        """
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
        """Get enricher prefix with trailing separator.

        Args:
            enricher_pipeline: Pipeline name in ``"provider_entity"`` format.

        Returns:
            Qualified prefix string in the form ``"provider.entity."`` or legacy
            ``"pipeline_"`` when pipeline name cannot be parsed.
        """
        return get_priority_enricher_prefix(enricher_pipeline)

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        return parse_pipeline_name(pipeline)

    @staticmethod
    def _resolve_priority_column(
        source: str,
        field: str,
        columns_set: set[str],
        seed_provider: str | None,
        seed_entity: str | None,
    ) -> str | None:
        """Resolve one priority token to a concrete column name."""
        return resolve_priority_column_helper(
            source=source,
            field=field,
            columns_set=columns_set,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
