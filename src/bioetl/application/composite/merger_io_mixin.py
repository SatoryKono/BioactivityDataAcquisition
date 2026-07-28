# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""I/O orchestration helpers for MergeService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.merger_output_mixin import MergeOutputWriterMixin
from bioetl.domain.composite.result import MergeResult

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

    import polars as pl

    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidator,
    )
    from bioetl.domain.composite import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.cross_validation import CrossValidationStats
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort


class MergeIOMixin(MergeOutputWriterMixin):
    """Mixin for merge cross-validation, output persistence, and result assembly."""

    # -- Host-class attributes (set by MergeService.__init__) --
    _config: MergeConfig
    _logger: LoggerPort
    _field_group_registry: FieldGroupRegistry | None
    _cross_validator: EnrichmentCrossValidator | None
    _gold_schema: Any | None  # Any: Pandera DataFrameModel class or instance
    _join_planner: JoinPlannerService
    _calculate_field_coverage: Callable[[pl.DataFrame], dict[str, float]]
    _count_fully_enriched: Callable[[pl.DataFrame, Sequence[EnricherConfig]], int]

    async def _apply_dependency_joins_if_needed(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig] | None,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        """Join dependencies only when both config and data are present."""
        if not dependencies or not dependency_dfs:
            return merged_df

        active_dependencies = [
            dep for dep in dependencies if dep.pipeline in dependency_dfs
        ]
        if not active_dependencies:
            return merged_df

        result = await self._join_planner.apply_dependency_joins(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=active_dependencies,
            seed_pipeline=seed_pipeline,
        )
        self._logger.info(
            "Applied dependency joins",
            dependencies_joined=len(active_dependencies),
            total_columns=len(result.columns),
        )
        return result

    def _run_cross_validation(
        self,
        merged_df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        enricher_dfs: dict[str, pl.DataFrame],
        effective_seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, CrossValidationStats | None, list[dict[str, object]]]:
        """Run optional seed-vs-enricher cross-validation and collect quarantine rows."""
        if self._cross_validator is None or not effective_seed_pipeline:
            return merged_df, None, []

        enricher_pipelines_joined = [
            enricher.pipeline
            for enricher in enrichers
            if enricher.pipeline in enricher_dfs
        ]
        if not enricher_pipelines_joined:
            return merged_df, None, []

        validated_df, cv_stats = self._cross_validator.validate(
            merged_df,
            enricher_pipelines_joined,
            effective_seed_pipeline,
        )
        quarantine_payloads = self._extract_quarantine_payloads(validated_df)
        output_df = self._drop_quarantined_rows(validated_df)
        return output_df, cv_stats, quarantine_payloads

    @staticmethod
    def _extract_quarantine_payloads(df: pl.DataFrame) -> list[dict[str, object]]:
        """Extract quarantine row payloads from _cv_quarantine marker column."""
        import polars as pl

        if "_cv_quarantine" not in df.columns:
            return []

        quarantine_df = df.filter(pl.col("_cv_quarantine"))
        if len(quarantine_df) == 0:
            return []

        quarantined_records: list[dict[str, object]] = quarantine_df.to_dicts()
        return quarantined_records

    @staticmethod
    def _drop_quarantined_rows(df: pl.DataFrame) -> pl.DataFrame:
        """Remove rows marked for cross-validation quarantine from persisted outputs."""
        import polars as pl

        if "_cv_quarantine" not in df.columns:
            return df
        return df.filter(~pl.col("_cv_quarantine"))

    async def _write_outputs(
        self,
        df: pl.DataFrame,
        metadata_timestamp: datetime | None,
        run_id: str,
        sources_used: list[str],
    ) -> None:
        """Write final merged dataset to Silver and Gold outputs."""
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=len(df),
        )
        await self._write_merged_silver(
            df,
            completed_at=metadata_timestamp,
            run_id=run_id,
            sources_used=sources_used,
        )

        self._logger.info(
            "Writing merged Gold table",
            path=self._config.output_gold_path,
            records=len(df),
        )
        await self._write_merged_gold(
            df,
            completed_at=metadata_timestamp,
            run_id=run_id,
            sources_used=sources_used,
        )

    def _build_merge_result(
        self,
        merged_df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        records_merged: int,
        records_from_seed: int,
        records_enriched: int,
        sources_used: list[str],
        duration_seconds: float,
        cv_stats: CrossValidationStats | None,
        quarantine_payloads: list[dict[str, object]],
    ) -> MergeResult:
        """Build MergeResult summary object from finalized merged DataFrame."""
        return MergeResult(
            records_merged=records_merged,
            records_from_seed=records_from_seed,
            records_enriched=records_enriched,
            records_fully_enriched=self._count_fully_enriched(merged_df, enrichers),
            sources_used=tuple(sources_used),
            field_coverage=self._calculate_field_coverage(merged_df),
            duration_seconds=duration_seconds,
            output_silver_path=self._config.output_silver_path,
            output_gold_path=self._config.output_gold_path,
            cross_validation_stats=cv_stats,
            quarantine_payloads=tuple(quarantine_payloads),
        )


__all__ = ["MergeIOMixin"]
