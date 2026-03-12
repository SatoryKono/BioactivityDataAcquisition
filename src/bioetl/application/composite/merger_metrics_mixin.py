"""Lineage and metrics helpers for MergeService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.join_planner_helpers import parse_pipeline_name

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

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> pl.DataFrame:
        """Add lineage metadata columns to DataFrame.

        Args:
            df: Merged DataFrame to annotate with lineage columns.
            enrichment_results: Map of enricher pipeline name to its execution result.
            run_id: Composite run identifier written to ``_composite_run_id``.
            sources_used: List of pipeline names that contributed data to the merge.
            dependency_results: Optional map of dependency pipeline name to its result,
                included in enrichment status when provided.

        Returns:
            DataFrame with ``_composite_run_id``, ``_source_providers``,
            ``_enrichment_status``, and ``_lineage_created_at`` columns appended.
        """
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
        """Drop columns configured for exclusion in merge config.

        Args:
            df: DataFrame from which excluded columns should be removed.

        Returns:
            DataFrame with columns matching ``exclude_fields`` glob patterns removed.
            Returns the original DataFrame unchanged when no patterns are configured.
        """
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
        """Count records with at least one enrichment value present.

        Args:
            df: Merged DataFrame to inspect for enrichment coverage.
            enrichers: Enricher configurations whose columns are checked for non-null values.
            seed_pipeline: Optional seed pipeline name (currently unused, reserved for future use).

        Returns:
            Number of rows where at least one enricher column contains a non-null value.
        """
        import polars as pl

        _ = seed_pipeline
        enricher_cols: list[str] = []

        for enricher in enrichers:
            try:
                provider, entity = parse_pipeline_name(enricher.pipeline)
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
        """Count records with all required enrichments.

        Args:
            df: Merged DataFrame to evaluate.
            enrichers: Enricher configurations defining required enrichment fields.

        Returns:
            Number of records fully enriched across all configured enrichers.
            Currently returns 0 (placeholder for future full-coverage logic).
        """
        _ = (df, enrichers)
        return 0

    def _calculate_field_coverage(self, df: pl.DataFrame) -> dict[str, float]:
        """Calculate percentage of non-null values per field.

        Args:
            df: DataFrame for which field coverage is computed.

        Returns:
            Dictionary mapping each non-private column name (not starting with ``_``)
            to its non-null ratio between 0.0 and 1.0. Returns an empty dict for
            empty DataFrames.
        """
        if len(df) == 0:
            return {}

        coverage: dict[str, float] = {}
        for col in df.columns:
            if not col.startswith("_"):
                non_null = len(df.filter(df[col].is_not_null()))
                coverage[col] = non_null / len(df)

        return coverage


__all__ = ["MergeMetricsRecorderMixin"]
