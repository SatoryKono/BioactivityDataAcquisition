"""Lineage and metrics helpers for MergeService."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime

import polars as pl

from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite import EnricherConfig, MergeConfig
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
        metadata_timestamp: datetime | None,
        sources_used: list[str],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> pl.DataFrame:
        """Add composite semantic metadata columns to DataFrame.

        Args:
            df: Merged DataFrame to annotate with lineage columns.
            enrichment_results: Map of enricher pipeline name to its execution result.
            run_id: Composite run identifier routed via explicit write kwargs.
            metadata_timestamp: Deterministic metadata timestamp routed via sidecars.
            sources_used: List of pipeline names that contributed data to the merge.
            dependency_results: Optional map of dependency pipeline name to its result,
                included in enrichment status when provided.

        Returns:
            DataFrame with ``_source_providers`` and ``_enrichment_status`` columns
            appended. Occurrence-scoped runtime anchors are kept out of canonical
            row payloads and travel separately via explicit write kwargs,
            sidecar metadata, lineage fragments, and control-plane artifacts.
        """
        import polars as pl

        _ = (run_id, metadata_timestamp)
        status_dict: dict[str, str] = {}
        if dependency_results:
            for name, dep_result in dependency_results.items():
                status_dict[name] = dep_result.status.value
        for name, enrich_result in enrichment_results.items():
            status_dict[name] = enrich_result.status.value

        return df.with_columns(
            [
                pl.lit(json.dumps(sources_used)).alias("_source_providers"),
                pl.lit(json.dumps(status_dict)).alias("_enrichment_status"),
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

    def _apply_field_mappings(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply configured source-to-canonical field mappings before projection."""
        if not self._config.field_mappings:
            return df

        result = df
        for source, target in self._config.field_mappings.items():
            if source not in result.columns or source == target:
                continue
            if target in result.columns:
                result = result.with_columns(
                    pl.coalesce(pl.col(source), pl.col(target)).alias(target)
                ).drop(source)
                continue
            result = result.rename({source: target})
        return result

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

        # Optimization: Use expr.sum() to count matching rows directly without materializing a filtered DataFrame.
        return int(df.select(any_enriched.sum()).item() or 0)

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
        total_rows = len(df)
        if total_rows == 0:
            return {}

        import polars as pl

        cols_to_check = [col for col in df.columns if not col.startswith("_")]
        if not cols_to_check:
            return {}

        # Optimization: Build expressions and execute once instead of Python loop with filter
        exprs = [
            (pl.col(col).is_not_null().sum() / total_rows).alias(col)
            for col in cols_to_check
        ]

        coverage_row = df.select(exprs).row(0, named=True)
        # Type coerce float values for strict typing compliance
        coverage = {k: float(v) for k, v in coverage_row.items()}

        return coverage


__all__ = ["MergeMetricsRecorderMixin"]
