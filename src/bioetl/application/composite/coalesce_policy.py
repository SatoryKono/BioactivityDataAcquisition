"""Coalescing policies for composite conflict resolution."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig
    from bioetl.domain.ports import LoggerPort


__all__ = ["CoalescePolicyService"]


class CoalescePolicyService:
    """Implements seed/enricher/explicit coalesce behaviors."""

    def __init__(
        self,
        logger: LoggerPort,
        priority_orderer: ColumnPriorityOrdererService,
    ) -> None:
        self._logger = logger
        self._priority_orderer = priority_orderer

    @staticmethod
    def extract_field_from_qualified(column: str) -> str:
        """Extract field name from qualified column (x.y.z -> z)."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]
        return column

    @staticmethod
    def can_coalesce(df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Check if two columns can be coalesced without type breakage."""
        import polars as pl

        type1 = df[col1].dtype
        type2 = df[col2].dtype

        if type1 == type2:
            return True

        if type1 == pl.Null or type2 == pl.Null:
            return True

        return isinstance(type1, pl.List) == isinstance(type2, pl.List)

    def coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        _enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce grouped columns while preferring seed columns first."""

        result = df
        seed_prefix = self._seed_prefix(seed_pipeline)
        field_groups = self._build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 4:
                continue

            sorted_cols = self._sort_columns(columns, seed_prefix, prefer_seed=True)
            compatible_cols = self._compatible_columns(result, sorted_cols)
            result = self._coalesce_and_drop(result, compatible_cols)

        return result

    def coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        _enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce grouped columns while preferring enricher columns first."""
        result = df
        seed_prefix = self._seed_prefix(seed_pipeline)
        field_groups = self._build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 1:
                continue

            sorted_cols = self._sort_columns(columns, seed_prefix, prefer_seed=False)
            compatible_cols = self._compatible_columns(result, sorted_cols)
            result = self._coalesce_and_drop(result, compatible_cols)

        return result

    def coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Currently equivalent to seed-priority coalescing."""
        return self.coalesce_prefer_seed(df, enrichers, seed_pipeline)

    def apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        field_priorities: dict[str, tuple[str, ...]],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply explicit source priority rules from config.field_priorities."""
        import polars as pl

        result = df
        available_columns = set(df.columns)

        for field, priorities in field_priorities.items():
            columns = self._priority_orderer.collect_field_columns(
                field,
                enrichers,
                available_columns,
                seed_pipeline,
            )
            if len(columns) <= 1:
                continue

            ordered_cols = self._priority_orderer.order_columns_by_priority(
                field,
                columns,
                priorities,
                seed_pipeline,
            )
            if not ordered_cols:
                continue

            compatible_cols, _incompatible_cols = (
                self._priority_orderer.filter_compatible_columns(
                    result,
                    field,
                    ordered_cols,
                    self.can_coalesce,
                )
            )
            if len(compatible_cols) > 1:
                target_col = compatible_cols[0]
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )

            cols_to_drop = [col for col in compatible_cols[1:] if col in result.columns]
            if cols_to_drop:
                result = result.drop(cols_to_drop)

        return result

    @staticmethod
    def _build_field_groups(df: pl.DataFrame) -> dict[str, list[str]]:
        """Group non-system columns by field name."""
        field_groups: dict[str, list[str]] = {}
        for col in df.columns:
            if col.startswith("_"):
                continue
            field = CoalescePolicyService.extract_field_from_qualified(col)
            field_groups.setdefault(field, []).append(col)
        return field_groups

    @staticmethod
    def _sort_columns(
        columns: list[str],
        seed_prefix: str | None,
        prefer_seed: bool,
    ) -> list[str]:
        """Sort columns with either seed-first or enricher-first strategy."""

        def sort_key(col: str) -> int:
            is_seed = bool(seed_prefix and col.startswith(seed_prefix))
            if prefer_seed:
                return 0 if is_seed else 1
            return 1 if is_seed else 0

        return sorted(columns, key=sort_key)

    @classmethod
    def _compatible_columns(
        cls, df: pl.DataFrame, ordered_cols: list[str]
    ) -> list[str]:
        """Keep the leading column and all columns type-compatible with it."""
        if not ordered_cols:
            return []

        base_col = ordered_cols[0]
        compatible_cols = [base_col]
        for col in ordered_cols[1:]:
            if cls.can_coalesce(df, base_col, col):
                compatible_cols.append(col)
        return compatible_cols

    @staticmethod
    def _coalesce_and_drop(
        df: pl.DataFrame, compatible_cols: list[str]
    ) -> pl.DataFrame:
        """Coalesce compatible columns into first and drop the rest."""
        import polars as pl

        if len(compatible_cols) <= 1:
            return df

        target_col = compatible_cols[0]
        result = df.with_columns(
            pl.coalesce(*[pl.col(col) for col in compatible_cols]).alias(target_col)
        )
        cols_to_drop = [col for col in compatible_cols[1:] if col in result.columns]
        if cols_to_drop:
            return result.drop(cols_to_drop)
        return result

    @staticmethod
    def _seed_prefix(seed_pipeline: str | None) -> str | None:
        """Build seed provider.entity prefix used for source ordering."""
        if not seed_pipeline:
            return None

        try:
            provider, entity = ColumnPriorityOrdererService._parse_pipeline_name(
                seed_pipeline
            )
            return f"{provider}.{entity}."
        except ValueError:
            return None


