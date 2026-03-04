"""Column priority ordering helpers for composite conflict resolution."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig
    from bioetl.domain.ports import LoggerPort


__all__ = ["ColumnPriorityOrdererService"]


class ColumnPriorityOrdererService:
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
        """Collect all qualified/legacy columns for a field from all sources."""
        columns: list[str] = []

        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
                seed_qualified = f"{seed_provider}.{seed_entity}.{field}"
                if seed_qualified in available_columns:
                    columns.append(seed_qualified)
            except ValueError:
                self._logger.debug(
                    "Could not parse seed pipeline for field collection",
                    seed_pipeline=seed_pipeline,
                    field=field,
                )

        for enricher in enrichers:
            try:
                provider, entity = self._parse_pipeline_name(enricher.pipeline)
                enricher_qualified = f"{provider}.{entity}.{field}"
                if (
                    enricher_qualified in available_columns
                    and enricher_qualified not in columns
                ):
                    columns.append(enricher_qualified)
            except ValueError:
                prefix = self.get_enricher_prefix(enricher.pipeline)
                legacy_col = f"{prefix}{field}".rstrip(".")
                if legacy_col in available_columns and legacy_col not in columns:
                    columns.append(legacy_col)

        return columns

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Order columns by configured source priority."""
        ordered_cols: list[str] = []
        columns_set = set(columns)

        seed_provider: str | None = None
        seed_entity: str | None = None
        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
            except ValueError:
                pass

        for source in priorities:
            qualified = self._resolve_priority_column(
                source,
                field,
                columns_set,
                seed_provider,
                seed_entity,
            )
            if qualified and qualified in columns_set and qualified not in ordered_cols:
                ordered_cols.append(qualified)

        for col in columns:
            if col not in ordered_cols:
                ordered_cols.append(col)

        return ordered_cols

    def filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
        can_coalesce: Callable[[pl.DataFrame, str, str], bool],
    ) -> tuple[list[str], list[str]]:
        """Filter columns to those compatible for coalescing."""
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
        """Get enricher prefix with trailing separator."""
        try:
            provider, entity = ColumnPriorityOrdererService._parse_pipeline_name(
                enricher_pipeline
            )
            return f"{provider}.{entity}."
        except ValueError:
            return f"{enricher_pipeline}_"

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        provider, entity = pipeline.split("_", 1)
        return provider, entity

    @staticmethod
    def _resolve_priority_column(
        source: str,
        field: str,
        columns_set: set[str],
        seed_provider: str | None,
        seed_entity: str | None,
    ) -> str | None:
        """Resolve one priority token to a concrete column name."""
        source_lower = source.lower()

        if source_lower == "seed":
            if seed_provider and seed_entity:
                return f"{seed_provider}.{seed_entity}.{field}"
            return None

        if "." in source:
            provider, entity = source.split(".", 1)
            return f"{provider.lower()}.{entity.lower()}.{field}"

        provider = source_lower
        if seed_provider and provider == seed_provider.lower() and seed_entity:
            return f"{provider}.{seed_entity}.{field}"

        for col in columns_set:
            if col.startswith(f"{provider}.") and col.endswith(f".{field}"):
                return col

        return None


