"""Column priority ordering helpers for composite conflict resolution."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import polars as pl

from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite.config import EnricherConfig
from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnPriorityOrderer"]


def get_enricher_prefix(enricher_pipeline: str) -> str:
    """Return qualified provider/entity prefix or legacy fallback prefix."""
    try:
        provider, entity = parse_pipeline_name(enricher_pipeline)
        return f"{provider}.{entity}."
    except ValueError:
        return f"{enricher_pipeline}_"


def resolve_seed_column(
    *,
    field: str,
    seed_provider: str | None,
    seed_entity: str | None,
) -> str | None:
    """Resolve the seed token to a qualified seed column when context exists."""
    if seed_provider and seed_entity:
        return f"{seed_provider}.{seed_entity}.{field}"
    return None


def resolve_by_column_scan(
    *,
    provider: str,
    field: str,
    columns_set: set[str],
) -> str | None:
    """Find a provider-prefixed column by scanning available columns."""
    for column in columns_set:
        if column.startswith(f"{provider}.") and column.endswith(f".{field}"):
            return column
    return None


def resolve_priority_column(
    *,
    source: str,
    field: str,
    columns_set: set[str],
    seed_provider: str | None,
    seed_entity: str | None,
) -> str | None:
    """Resolve one priority token to a concrete column name."""
    source_lower = source.lower()
    if source_lower == "seed":
        return resolve_seed_column(
            field=field,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
    if "." in source:
        provider, entity = source.split(".", 1)
        return f"{provider.lower()}.{entity.lower()}.{field}"
    provider = source_lower
    if seed_provider and provider == seed_provider.lower() and seed_entity:
        return f"{provider}.{seed_entity}.{field}"
    return resolve_by_column_scan(
        provider=provider,
        field=field,
        columns_set=columns_set,
    )


def collect_priority_field_columns(
    *,
    field: str,
    enrichers: Sequence[EnricherConfig],
    available_columns: set[str],
    seed_pipeline: str | None = None,
) -> tuple[list[str], bool]:
    """Collect candidate field columns and indicate whether parsing fallback was used."""
    columns: list[str] = []
    used_parse_fallback = False
    if seed_pipeline:
        try:
            seed_provider, seed_entity = parse_pipeline_name(seed_pipeline)
            seed_qualified = f"{seed_provider}.{seed_entity}.{field}"
            if seed_qualified in available_columns:
                columns.append(seed_qualified)
        except ValueError:
            used_parse_fallback = True
    for enricher in enrichers:
        try:
            provider, entity = parse_pipeline_name(enricher.pipeline)
            enricher_qualified = f"{provider}.{entity}.{field}"
            if (
                enricher_qualified in available_columns
                and enricher_qualified not in columns
            ):
                columns.append(enricher_qualified)
        except ValueError:
            legacy_col = f"{get_enricher_prefix(enricher.pipeline)}{field}".rstrip(".")
            if legacy_col in available_columns and legacy_col not in columns:
                columns.append(legacy_col)
    return columns, used_parse_fallback


def order_priority_columns(
    *,
    field: str,
    columns: list[str],
    priorities: Sequence[str],
    seed_pipeline: str | None = None,
) -> tuple[list[str], bool]:
    """Order columns by source priority and indicate seed-pipeline parse fallback."""
    ordered_cols: list[str] = []
    columns_set = set(columns)
    seed_provider: str | None = None
    seed_entity: str | None = None
    used_parse_fallback = False
    if seed_pipeline:
        try:
            seed_provider, seed_entity = parse_pipeline_name(seed_pipeline)
        except ValueError:
            used_parse_fallback = True
    for source in priorities:
        qualified = resolve_priority_column(
            source=source,
            field=field,
            columns_set=columns_set,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
        if qualified and qualified in columns_set and qualified not in ordered_cols:
            ordered_cols.append(qualified)
    for column in columns:
        if column not in ordered_cols:
            ordered_cols.append(column)
    return ordered_cols, used_parse_fallback


class ColumnPriorityOrderer:
    """Resolves source column ordering for explicit field priority rules.

    .. deprecated:: 2024.2
        Use :class:`ColumnOrderService` instead for unified column ordering functionality.
    """

    def __init__(self, logger: LoggerPort) -> None:
        import warnings

        warnings.warn(
            "ColumnPriorityOrderer is deprecated and will be removed in a future version. "
            "Use ColumnOrderService instead for unified column ordering functionality.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        return get_enricher_prefix(enricher_pipeline)

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
        return resolve_priority_column(
            source=source,
            field=field,
            columns_set=columns_set,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
