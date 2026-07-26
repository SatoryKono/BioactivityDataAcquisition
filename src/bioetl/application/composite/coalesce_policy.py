"""Coalescing policies for composite conflict resolution."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite._coalesce_policy_support import (
    _ColumnPriorityProvider,
    apply_field_priority,
    build_field_groups,
    can_coalesce,
    coalesce_and_drop,
    coalesce_by_latest_timestamp,
    compatible_columns,
    extract_field_from_qualified,
    resolve_priority_provider,
    seed_prefix,
    sort_columns,
)
from bioetl.application.composite.column_service import ColumnOrderService

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite import EnricherConfig
    from bioetl.domain.ports import LoggerPort


__all__ = ["CoalescePolicyService"]


class CoalescePolicyService:
    """Implements seed/enricher/explicit coalesce behaviors."""

    def __init__(
        self,
        logger: LoggerPort,
        priority_orderer: _ColumnPriorityProvider | None = None,
        order_service: ColumnOrderService | None = None,
    ) -> None:
        self._logger = logger
        self._priority_orderer = priority_orderer
        self._order_service = order_service

    @staticmethod
    def extract_field_from_qualified(column: str) -> str:
        """Extract field name from qualified column (x.y.z -> z).

        Args:
            column: Qualified column name, e.g. ``"provider.entity.field"``.

        Returns:
            Unqualified field name string.
        """
        return extract_field_from_qualified(column)

    @staticmethod
    def can_coalesce(df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Check if two columns can be coalesced without type breakage.

        Args:
            df: DataFrame containing both columns.
            col1: Name of the first column.
            col2: Name of the second column.

        Returns:
            True if the columns are type-compatible for coalescing, False otherwise.
        """
        return can_coalesce(df, col1, col2)

    _compatible_columns = staticmethod(compatible_columns)
    _coalesce_and_drop = staticmethod(coalesce_and_drop)
    _seed_prefix = staticmethod(seed_prefix)

    def coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        _enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce grouped columns while preferring seed columns first.

        Args:
            df: DataFrame with potentially duplicate qualified field columns.
            _enrichers: Enricher configurations (unused, kept for API symmetry).
            seed_pipeline: Pipeline name used to identify seed columns.

        Returns:
            DataFrame with duplicate field columns coalesced, seed values preferred.
        """

        result = df
        seed_prefix_value = seed_prefix(seed_pipeline)
        field_groups = build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 4:
                continue

            sorted_cols = sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=True,
            )
            result = coalesce_and_drop(
                result,
                compatible_columns(result, sorted_cols),
            )

        return result

    def coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        _enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce grouped columns while preferring enricher columns first.

        Args:
            df: DataFrame with potentially duplicate qualified field columns.
            _enrichers: Enricher configurations (unused, kept for API symmetry).
            seed_pipeline: Pipeline name used to identify seed columns.

        Returns:
            DataFrame with duplicate field columns coalesced, enricher values preferred.
        """
        result = df
        seed_prefix_value = seed_prefix(seed_pipeline)
        field_groups = build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 1:
                continue

            sorted_cols = sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=False,
            )
            result = coalesce_and_drop(
                result,
                compatible_columns(result, sorted_cols),
            )

        return result

    def coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Currently equivalent to seed-priority coalescing.

        Args:
            df: DataFrame with potentially duplicate qualified field columns.
            enrichers: Enricher configurations forwarded to the seed-priority implementation.
            seed_pipeline: Pipeline name used to identify seed columns.

        Returns:
            DataFrame with duplicate field columns coalesced using seed-priority order.
        """
        return self.coalesce_prefer_seed(df, enrichers, seed_pipeline)

    def coalesce_prefer_latest_timestamp(
        self,
        df: pl.DataFrame,
        _enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce grouped columns by the newest available companion timestamp.

        When no sufficient timestamp companions are available for a field group,
        the method falls back to the same deterministic seed-priority ordering
        used by the standard coalesce path.
        """
        result = df
        seed_prefix_value = seed_prefix(seed_pipeline)
        for columns in build_field_groups(result).values():
            if len(columns) <= 1:
                continue
            ordered_cols = sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=True,
            )
            result = coalesce_by_latest_timestamp(
                result,
                ordered_cols=ordered_cols,
            )
        return result

    def apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        field_priorities: dict[str, tuple[str, ...]],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply explicit source priority rules from config.field_priorities.

        Args:
            df: DataFrame with potentially duplicate qualified field columns.
            enrichers: Enricher configurations used to locate per-source columns.
            field_priorities: Mapping of field name to ordered tuple of source names.
            seed_pipeline: Pipeline name used to identify seed columns.

        Returns:
            DataFrame with field columns coalesced according to the explicit priority rules.
        """

        result = df
        available_columns = set(df.columns)
        provider = resolve_priority_provider(
            self._priority_orderer,
            self._order_service,
        )
        for field, priorities in field_priorities.items():
            result = apply_field_priority(
                result,
                provider=provider,
                field=field,
                priorities=priorities,
                enrichers=enrichers,
                available_columns=available_columns,
                seed_pipeline=seed_pipeline,
                can_coalesce_fn=self.can_coalesce,
            )

        return result
