"""Enricher deduplication logic for composite pipelines.

Provides functionality to deduplicate enricher tables before join
to prevent fan-out when enricher has duplicate values by join keys.
"""

from __future__ import annotations

import polars as pl

from bioetl.domain.ports import LoggerPort
from bioetl.domain.run_reports.context import get_stage_accounting
from bioetl.domain.run_reports.models import StageId

__all__ = ["EnricherDeduplicatorService"]


class EnricherDeduplicatorService:
    """Handles deduplication of enricher tables before join operations."""

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize deduplicator with logger.

        Args:
            logger: Logger port for warning messages.
        """
        self._logger = logger

    def deduplicate(
        self,
        enricher_df: pl.DataFrame,
        join_keys: list[str],
        enricher_name: str,
    ) -> pl.DataFrame:
        """Check and deduplicate enricher before join.

        Workflow:
        1. Check for duplicates by join_keys
        2. If no duplicates → return df unchanged
        3. If duplicates exist → aggregate and log

        Args:
            enricher_df: Enricher DataFrame.
            join_keys: Columns for join (grouping keys).
            enricher_name: Name for logging.

        Returns:
            DataFrame with unique values by join_keys.
        """
        if not self._check_duplicates(enricher_df, join_keys):
            return enricher_df
        return self._aggregate_duplicates(enricher_df, join_keys, enricher_name)

    def _check_duplicates(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
    ) -> bool:
        """Check for duplicates by key columns."""
        if len(df) == 0:
            return False
        missing_cols = [c for c in key_columns if c not in df.columns]
        if missing_cols:
            return False
        unique_count: int = df.select(key_columns).n_unique()
        has_duplicates: bool = unique_count < len(df)
        return has_duplicates

    def _aggregate_duplicates(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
        enricher_name: str,
    ) -> pl.DataFrame:
        """Aggregate duplicates by merging differing values."""

        records_before = len(df)
        non_key_columns = [c for c in df.columns if c not in key_columns]

        if not non_key_columns:
            # OPTIMIZATION: maintain_order=False avoids high FFI overhead for large cardinality data.
            # We explicitly sort afterwards to ensure deterministic output.
            result = df.select(key_columns).unique(maintain_order=False).sort(key_columns)
            self._record_deduplicated(records_before - len(result))
            self._log_deduplication(
                enricher_name, key_columns, records_before, len(result), []
            )
            return result

        columns_with_conflicts, columns_without_conflicts = self._classify_columns(
            df, key_columns, non_key_columns
        )

        agg_exprs = self._build_aggregation_exprs(
            df, columns_with_conflicts, columns_without_conflicts
        )

        # OPTIMIZATION: maintain_order=False avoids high FFI overhead for large cardinality data.
        # We explicitly sort afterwards to ensure deterministic output.
        result = df.group_by(key_columns, maintain_order=False).agg(agg_exprs).sort(key_columns)
        self._record_deduplicated(records_before - len(result))

        self._log_deduplication(
            enricher_name,
            key_columns,
            records_before,
            len(result),
            columns_with_conflicts,
        )
        return result

    @staticmethod
    def _record_deduplicated(count: int) -> None:
        """Record composite deduplication in the active pipeline report."""
        accounting = get_stage_accounting()
        if accounting is not None and count > 0:
            accounting.record_removal(
                StageId.SILVER.value,
                outcome="deduplicated",
                reason_code="DEDUP_KEY_COLLISION",
                count=count,
            )

    def _classify_columns(
        self,
        df: pl.DataFrame,
        key_columns: list[str],
        non_key_columns: list[str],
    ) -> tuple[list[str], list[str]]:
        """Classify columns into those with and without conflicts.

        Performs a single group_by with all column aggregations combined,
        instead of N separate group_by operations (one per column).
        """
        import polars as pl

        if not non_key_columns:
            return [], []

        # Build all conflict-detection aggregations in one pass
        agg_exprs: list[pl.Expr] = []
        for col in non_key_columns:
            agg_exprs.append(
                pl.col(col).drop_nulls().n_unique().alias(f"{col}__n_unique")
            )
            agg_exprs.append(pl.col(col).is_null().any().alias(f"{col}__has_null"))
            agg_exprs.append(pl.col(col).is_null().all().alias(f"{col}__all_null"))

        aggregated = df.group_by(key_columns).agg(agg_exprs)
        if aggregated.is_empty():
            return [], list(non_key_columns)

        # Classify each column based on the single aggregation result
        columns_with_conflicts: list[str] = []
        columns_without_conflicts: list[str] = []

        if not non_key_columns:
            return columns_with_conflicts, columns_without_conflicts

        # One select/.any() pass instead of N filter().height FFI crossings.
        conflict_exprs = [
            (
                (pl.col(f"{col}__n_unique") > 1)
                | (pl.col(f"{col}__has_null") & ~pl.col(f"{col}__all_null"))
            )
            .any()
            .alias(col)
            for col in non_key_columns
        ]
        conflict_results = aggregated.select(conflict_exprs).row(0, named=True)
        columns_with_conflicts = [
            col for col in non_key_columns if conflict_results[col]
        ]
        columns_without_conflicts = [
            col for col in non_key_columns if not conflict_results[col]
        ]
        return columns_with_conflicts, columns_without_conflicts

    def _build_aggregation_exprs(
        self,
        df: pl.DataFrame,
        columns_with_conflicts: list[str],
        columns_without_conflicts: list[str],
    ) -> list[pl.Expr]:
        """Build aggregation expressions for all columns."""
        import polars as pl

        agg_exprs: list[pl.Expr] = []
        for col in columns_without_conflicts:
            agg_exprs.append(pl.col(col).first().alias(col))
        for col in columns_with_conflicts:
            agg_exprs.append(self._build_concat_expr(col, df.schema[col]))
        return agg_exprs

    def _build_concat_expr(self, column: str, dtype: pl.DataType) -> pl.Expr:
        """Build expression that concatenates values with |.

        Note: Values are NOT sorted and duplicates are NOT removed.
        The order is preserved from the original data.
        """
        import polars as pl

        as_string = self._to_string_expr(column, dtype)
        return (
            pl.when(pl.col(column).is_null())
            .then(pl.lit("null"))
            .otherwise(as_string)
            .str.join("|")
            .alias(column)
        )

    def _to_string_expr(self, column: str, dtype: pl.DataType) -> pl.Expr:
        """Convert column to string expression."""
        import polars as pl

        col_expr = pl.col(column)

        if isinstance(dtype, (pl.List, pl.Struct)):
            return col_expr.map_elements(
                lambda x: str(x) if x is not None else None, return_dtype=pl.String
            )
        if dtype == pl.Boolean:
            return (
                pl.when(col_expr.is_null())
                .then(pl.lit(None))
                .when(col_expr)
                .then(pl.lit("true"))
                .otherwise(pl.lit("false"))
            )
        if isinstance(dtype, pl.Datetime):
            return col_expr.dt.to_string("%Y-%m-%dT%H:%M:%SZ")
        return col_expr.cast(pl.String)

    def _log_deduplication(
        self,
        enricher_name: str,
        key_columns: list[str],
        records_before: int,
        records_after: int,
        columns_with_conflicts: list[str],
    ) -> None:
        """Log deduplication results."""
        self._logger.warning(
            "Duplicates aggregated in enricher",
            enricher=enricher_name,
            join_keys=key_columns,
            duplicate_count=records_before - records_after,
            records_before=records_before,
            records_after=records_after,
            columns_with_conflicts=columns_with_conflicts,
        )
