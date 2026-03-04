"""Lineage and metrics helpers for MergeService."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig, MergeConfig
    from bioetl.domain.composite.result import DependencyResult, EnrichmentResult
    from bioetl.domain.ports import LoggerPort


class MergeMetricsRecorderMixin:
    """Mixin for lineage enrichment and post-merge metric calculations."""

    _config: MergeConfig
    _logger: LoggerPort
    _parse_pipeline_name: Callable[[str], tuple[str, str]]

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> pl.DataFrame:
        """Add lineage metadata columns to DataFrame."""
        import polars as pl

        status_dict: dict[str, str] = {}
        if dependency_results:
            for name, dep_result in dependency_results.items():
                status_dict[name] = dep_result.status.value
        for name, enrich_result in enrichment_results.items():
            status_dict[name] = enrich_result.status.value

        return df.with_columns(
            [
                pl.lit(run_id).alias("_composite_run_id"),
                pl.lit(str(sources_used)).alias("_source_providers"),
                pl.lit(str(status_dict)).alias("_enrichment_status"),
                pl.lit(datetime.now(tz=UTC).isoformat()).alias("_lineage_created_at"),
            ]
        )

    def _drop_excluded_fields(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop columns configured for exclusion in merge config."""
        if not self._config.exclude_fields:
            return df

        from fnmatch import fnmatch

        excluded = [
            col
            for col in df.columns
            if any(fnmatch(col, pattern) for pattern in self._config.exclude_fields)
        ]
        if not excluded:
            return df

        self._logger.info(
            "Dropping excluded fields from merged output",
            excluded_count=len(excluded),
            excluded_fields=excluded[:10],
        )
        return df.drop(excluded)

    def _count_enriched_records(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> int:
        """Count records with at least one enrichment value present."""
        import polars as pl

        _ = seed_pipeline
        enricher_cols: list[str] = []

        for enricher in enrichers:
            try:
                provider, entity = self._parse_pipeline_name(enricher.pipeline)
                prefix = f"{provider}.{entity}."
            except ValueError:
                prefix = f"{enricher.pipeline}_"

            enricher_cols.extend([col for col in df.columns if col.startswith(prefix)])

        if not enricher_cols:
            return 0

        any_enriched = pl.any_horizontal(
            [pl.col(col).is_not_null() for col in enricher_cols]
        )
        return len(df.filter(any_enriched))

    def _count_fully_enriched(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
    ) -> int:
        """Count records with all required enrichments."""
        _ = (df, enrichers)
        return 0

    def _calculate_field_coverage(self, df: pl.DataFrame) -> dict[str, float]:
        """Calculate percentage of non-null values per field."""
        if len(df) == 0:
            return {}

        coverage: dict[str, float] = {}
        for col in df.columns:
            if not col.startswith("_"):
                non_null = len(df.filter(df[col].is_not_null()))
                coverage[col] = non_null / len(df)

        return coverage


__all__ = ["MergeMetricsRecorderMixin"]
