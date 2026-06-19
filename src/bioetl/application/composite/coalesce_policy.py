"""Coalescing policies for composite conflict resolution."""

from __future__ import annotations

from datetime import date, datetime
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig
    from bioetl.domain.ports import LoggerPort


__all__ = ["CoalescePolicyService"]

_TIMESTAMP_FIELD_SUFFIXES = (
    "updated_at",
    "modified_at",
    "last_updated",
    "timestamp",
    "publication_date",
    "created_at",
)


class _ColumnPriorityProvider(Protocol):
    """Shared priority-ordering surface exposed by ``ColumnOrderService``."""

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None,
    ) -> list[str]: ...

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: tuple[str, ...],
        seed_pipeline: str | None,
    ) -> list[str]: ...

    def filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
        _can_coalesce_fn: Callable[[pl.DataFrame, str, str], bool],
    ) -> tuple[list[str], list[str]]: ...


def extract_field_from_qualified(column: str) -> str:
    """Extract field name from qualified column (x.y.z -> z)."""
    parts = column.split(".")
    if len(parts) == 3:
        return parts[2]
    return column


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


def build_field_groups(df: pl.DataFrame) -> dict[str, list[str]]:
    """Group non-system columns by field name."""
    field_groups: dict[str, list[str]] = {}
    for col in df.columns:
        if col.startswith("_"):
            continue
        field = extract_field_from_qualified(col)
        field_groups.setdefault(field, []).append(col)
    return field_groups


def sort_columns(
    columns: list[str],
    seed_prefix_value: str | None,
    *,
    prefer_seed: bool,
) -> list[str]:
    """Sort columns with either seed-first or enricher-first strategy."""

    def sort_key(col: str) -> int:
        is_seed = bool(seed_prefix_value and col.startswith(seed_prefix_value))
        if prefer_seed:
            return 0 if is_seed else 1
        return 1 if is_seed else 0

    return sorted(columns, key=sort_key)


def compatible_columns(df: pl.DataFrame, ordered_cols: list[str]) -> list[str]:
    """Keep the leading column and all columns type-compatible with it."""
    if not ordered_cols:
        return []

    base_col = ordered_cols[0]
    result = [base_col]
    for col in ordered_cols[1:]:
        if can_coalesce(df, base_col, col):
            result.append(col)
    return result


def coalesce_and_drop(df: pl.DataFrame, compatible_cols: list[str]) -> pl.DataFrame:
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


def seed_prefix(seed_pipeline: str | None) -> str | None:
    """Build seed provider.entity prefix used for source ordering."""
    if not seed_pipeline:
        return None

    try:
        provider, entity = parse_pipeline_name(seed_pipeline)
        return f"{provider}.{entity}."
    except ValueError:
        return None


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
        seed_prefix_value = self._seed_prefix(seed_pipeline)
        field_groups = self._build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 4:
                continue

            sorted_cols = self._sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=True,
            )
            compatible_cols = self._compatible_columns(result, sorted_cols)
            result = self._coalesce_and_drop(result, compatible_cols)

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
        seed_prefix_value = self._seed_prefix(seed_pipeline)
        field_groups = self._build_field_groups(result)

        for columns in field_groups.values():
            if len(columns) <= 1:
                continue

            sorted_cols = self._sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=False,
            )
            compatible_cols = self._compatible_columns(result, sorted_cols)
            result = self._coalesce_and_drop(result, compatible_cols)

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
        seed_prefix_value = self._seed_prefix(seed_pipeline)
        for columns in self._build_field_groups(result).values():
            if len(columns) <= 1:
                continue
            ordered_cols = self._sort_columns(
                columns,
                seed_prefix_value,
                prefer_seed=True,
            )
            result = self._coalesce_by_latest_timestamp(
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
        provider = self._resolve_priority_provider()
        for field, priorities in field_priorities.items():
            result = self._apply_field_priority(
                result,
                provider=provider,
                field=field,
                priorities=priorities,
                enrichers=enrichers,
                available_columns=available_columns,
                seed_pipeline=seed_pipeline,
            )

        return result

    def _resolve_priority_provider(self) -> _ColumnPriorityProvider:
        """Return the preferred column ordering implementation."""
        if self._order_service is not None:
            return self._order_service
        assert self._priority_orderer is not None
        return self._priority_orderer

    def _apply_field_priority(
        self,
        df: pl.DataFrame,
        *,
        provider: _ColumnPriorityProvider,
        field: str,
        priorities: tuple[str, ...],
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        """Apply one explicit field-priority rule and return updated DataFrame."""
        columns = provider.collect_field_columns(
            field,
            enrichers,
            available_columns,
            seed_pipeline,
        )
        if len(columns) <= 1:
            return df

        ordered_cols = provider.order_columns_by_priority(
            field,
            columns,
            priorities,
            seed_pipeline,
        )
        if not ordered_cols:
            return df

        compatible_cols, _incompatible_cols = provider.filter_compatible_columns(
            df,
            field,
            ordered_cols,
            self.can_coalesce,
        )
        return self._coalesce_and_drop(df, compatible_cols)

    @staticmethod
    def _build_field_groups(df: pl.DataFrame) -> dict[str, list[str]]:
        """Group non-system columns by field name."""
        return build_field_groups(df)

    @staticmethod
    def _sort_columns(
        columns: list[str],
        seed_prefix: str | None,
        prefer_seed: bool,
    ) -> list[str]:
        """Sort columns with either seed-first or enricher-first strategy."""
        return sort_columns(columns, seed_prefix, prefer_seed=prefer_seed)

    @classmethod
    def _compatible_columns(
        cls, df: pl.DataFrame, ordered_cols: list[str]
    ) -> list[str]:
        """Keep the leading column and all columns type-compatible with it."""
        return compatible_columns(df, ordered_cols)

    @staticmethod
    def _coalesce_and_drop(
        df: pl.DataFrame, compatible_cols: list[str]
    ) -> pl.DataFrame:
        """Coalesce compatible columns into first and drop the rest."""
        return coalesce_and_drop(df, compatible_cols)

    @classmethod
    def _coalesce_by_latest_timestamp(
        cls,
        df: pl.DataFrame,
        *,
        ordered_cols: list[str],
    ) -> pl.DataFrame:
        """Coalesce compatible columns using companion timestamps when present."""
        import polars as pl

        compatible_cols = cls._compatible_columns(df, ordered_cols)
        if len(compatible_cols) <= 1:
            return df

        timestamp_columns = {
            column: cls._resolve_timestamp_companion(column, set(df.columns))
            for column in compatible_cols
        }
        if sum(1 for value in timestamp_columns.values() if value is not None) < 2:
            return cls._coalesce_and_drop(df, compatible_cols)

        target_col = compatible_cols[0]
        row_fields = list(
            dict.fromkeys(
                [
                    *compatible_cols,
                    *(
                        timestamp_col
                        for timestamp_col in timestamp_columns.values()
                        if timestamp_col is not None
                    ),
                ]
            )
        )
        priority_rank = {column: index for index, column in enumerate(compatible_cols)}

        result = df.with_columns(
            pl.struct(row_fields).map_elements(
                lambda row: cls._pick_latest_timestamp_value(
                    row=row,
                    compatible_cols=compatible_cols,
                    timestamp_columns=timestamp_columns,
                    priority_rank=priority_rank,
                ),
                return_dtype=df.schema[target_col],
            ).alias(target_col)
        )
        cols_to_drop = [column for column in compatible_cols[1:] if column in result.columns]
        return result.drop(cols_to_drop) if cols_to_drop else result

    @staticmethod
    def _resolve_timestamp_companion(
        column: str,
        available_columns: set[str],
    ) -> str | None:
        """Resolve the companion timestamp column for one qualified value column."""
        parts = column.split(".")
        if len(parts) < 3:
            return None
        prefix = ".".join(parts[:-1])
        for suffix in _TIMESTAMP_FIELD_SUFFIXES:
            candidate = f"{prefix}.{suffix}"
            if candidate != column and candidate in available_columns:
                return candidate
        return None

    @classmethod
    def _pick_latest_timestamp_value(
        cls,
        *,
        row: dict[str, Any],  # Any: Row values can be of any type (str, int, float, etc.)
        compatible_cols: list[str],
        timestamp_columns: dict[str, str | None],
        priority_rank: dict[str, int],
    ) -> Any:  # Any: Return type matches the polymorphic row value type
        """Pick the newest non-null field value from one row deterministically."""
        fallback_value: Any = None  # Any: Can hold any row value type during comparison
        fallback_rank: int | None = None
        best_value: Any = None  # Any: Can hold any row value type during comparison
        best_rank: int | None = None
        best_timestamp_key: tuple[int, float | str] | None = None

        for column in compatible_cols:
            value = row.get(column)
            if value is None:
                continue
            rank = priority_rank[column]
            if fallback_rank is None or rank < fallback_rank:
                fallback_value = value
                fallback_rank = rank

            timestamp_column = timestamp_columns.get(column)
            if timestamp_column is None:
                continue
            timestamp_value = row.get(timestamp_column)
            if timestamp_value is None:
                continue

            timestamp_key = cls._timestamp_sort_key(timestamp_value)
            if best_timestamp_key is None or timestamp_key > best_timestamp_key:
                best_value = value
                best_rank = rank
                best_timestamp_key = timestamp_key
                continue
            if (
                timestamp_key == best_timestamp_key
                and best_rank is not None
                and rank < best_rank
            ):
                best_value = value
                best_rank = rank

        return best_value if best_value is not None else fallback_value

    @staticmethod
    def _timestamp_sort_key(value: object) -> tuple[int, float | str]:
        """Normalize mixed timestamp-like values into a deterministic sort key."""
        if isinstance(value, datetime):
            return (3, value.timestamp())
        if isinstance(value, date):
            return (3, float(value.toordinal()))
        if isinstance(value, int | float):
            return (2, float(value))
        if isinstance(value, str):
            return (1, value)
        return (0, "")

    @staticmethod
    def _seed_prefix(seed_pipeline: str | None) -> str | None:
        """Build seed provider.entity prefix used for source ordering."""
        return seed_prefix(seed_pipeline)
