"""Enricher aggregator for 1:M relationships in composite pipelines.

Provides functionality to aggregate multiple rows per join key into a single
row before joining with seed data. See ADR-026.
"""

from __future__ import annotations

import polars as pl

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.ports import LoggerPort

__all__ = ["EnricherAggregator"]


_ORDER_SENSITIVE_FUNCTIONS = frozenset(
    {
        AggregationFunction.COLLECT_LIST,
        AggregationFunction.COLLECT_SET,
        AggregationFunction.FIRST,
        AggregationFunction.CONCAT_STR,
    }
)


def _deduplicate_columns(columns: list[str]) -> list[str]:
    """Return columns in first-seen order with duplicates removed."""
    # PERF: Using dict.fromkeys() is ~4x faster than an O(n^2) list lookup loop
    # and preserves first-seen insertion order natively via C-level dicts.
    return list(dict.fromkeys(columns))


class EnricherAggregator:
    """Aggregates 1:M enricher data into 1:1 before join."""

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize the aggregator.

        Args:
            logger: Logger port for structured logging.
        """
        self._logger = logger

    def aggregate(
        self,
        df: pl.DataFrame,
        config: AggregationConfig,
        enricher_name: str,
    ) -> pl.DataFrame:
        """Aggregate 1:M enricher data into 1:1 before join.

        Args:
            df: Enricher DataFrame with multiple rows per join key.
            config: Aggregation configuration.
            enricher_name: Enricher name for logging.

        Returns:
            DataFrame with one row per join key.
        """
        self._logger.debug(
            "Aggregating enricher data",
            enricher=enricher_name,
            rows_before=len(df),
            group_by=config.group_by,
            order_by=config.order_by,
            field_count=len(config.fields),
        )

        ordered_df = self._sort_for_deterministic_aggregation(df, config)
        agg_exprs: list[pl.Expr] = []

        for field_spec in config.fields:
            expr = self._build_aggregation_expr(field_spec)
            agg_exprs.append(expr)

        result = ordered_df.group_by(config.group_by, maintain_order=True).agg(
            agg_exprs
        )
        result = result.sort(config.group_by)

        self._logger.info(
            "Aggregated enricher data",
            enricher=enricher_name,
            rows_before=len(df),
            rows_after=len(result),
            group_by=config.group_by,
            order_by=config.order_by,
        )

        return result

    def _sort_for_deterministic_aggregation(
        self,
        df: pl.DataFrame,
        config: AggregationConfig,
    ) -> pl.DataFrame:
        """Sort rows before group aggregation so list/first/string outputs are stable."""
        sort_columns = self._resolve_sort_columns(config)
        available_columns = [column for column in sort_columns if column in df.columns]
        if not available_columns:
            return df
        return df.sort(available_columns)

    def _resolve_sort_columns(self, config: AggregationConfig) -> list[str]:
        """Return canonical sort keys, defaulting to aggregated source fields."""
        order_columns = list(config.order_by)
        if not order_columns:
            order_columns.extend(
                field.source_field
                for field in config.fields
                if field.agg_function in _ORDER_SENSITIVE_FUNCTIONS
            )
        return _deduplicate_columns([config.group_by, *order_columns])

    def _build_aggregation_expr(self, spec: AggregationFieldSpec) -> pl.Expr:
        """Build Polars expression for a single aggregation field."""
        import polars as pl

        output_name = spec.effective_output_field
        base_col = pl.col(spec.source_field)

        if spec.filter_condition:
            filter_expr = self._parse_filter_condition(spec.filter_condition)
            if filter_expr is not None:
                base_col = base_col.filter(filter_expr)

        match spec.agg_function:
            case AggregationFunction.COLLECT_LIST:
                expr = base_col.drop_nulls()
            case AggregationFunction.COLLECT_SET:
                expr = base_col.drop_nulls().unique().sort()
            case AggregationFunction.COUNT:
                expr = base_col.count()
            case AggregationFunction.FIRST:
                expr = base_col.first()
            case AggregationFunction.CONCAT_STR:
                expr = base_col.drop_nulls().cast(pl.Utf8).str.join(", ")
            case _:
                expr = base_col

        return expr.alias(output_name)

    def _parse_filter_condition(self, condition: str) -> pl.Expr | None:
        """Parse a simple filter condition into a Polars expression."""
        import polars as pl

        condition = condition.strip()
        upper_condition = condition.upper()

        if " IS NOT NULL" in upper_condition:
            field = condition[: upper_condition.find(" IS NOT NULL")].strip()
            return pl.col(field).is_not_null()

        if " IS NULL" in upper_condition:
            field = condition[: upper_condition.find(" IS NULL")].strip()
            return pl.col(field).is_null()

        if " == " in condition:
            parts = condition.split(" == ", 1)
            if len(parts) == 2:
                field = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                return pl.col(field) == value

        if " != " in condition:
            parts = condition.split(" != ", 1)
            if len(parts) == 2:
                field = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                return pl.col(field) != value

        self._logger.warning(
            "Could not parse filter condition",
            condition=condition,
        )
        return None
