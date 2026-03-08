"""I/O and load/write helpers for MergeService."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.merger_output_mixin import MergeOutputWriterMixin
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidationService,
    )
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.cross_validation import CrossValidationStats
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
    )
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort, StoragePort


_MERGE_READ_ERRORS = (
    StorageError,
    NetworkError,
    CheckpointConflictError,
    DataQualityError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


def _path_to_table_name_local(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeIOMixin(MergeOutputWriterMixin):
    """Mixin for merge data loading, cross-validation, and output persistence."""

    # -- Host-class attributes (set by MergeService.__init__) --
    _config: MergeConfig
    _logger: LoggerPort
    _storage: StoragePort
    _delta_reader: DeltaReaderPort | None
    _field_group_registry: FieldGroupRegistry | None
    _cross_validator: EnrichmentCrossValidationService | None
    _gold_schema: Any | None  # Any: Pandera DataFrameModel class or instance
    _join_planner: JoinPlannerService
    _renamer: ColumnRenamerService
    _get_field_aliases: Callable[[str], dict[str, str] | None]
    _infer_pipeline_from_table: Callable[[str], str | None]
    _infer_silver_table: Callable[[str], str]
    _calculate_field_coverage: Callable[[pl.DataFrame], dict[str, float]]
    _count_fully_enriched: Callable[[pl.DataFrame, Sequence[EnricherConfig]], int]

    async def _prepare_seed_dataframe(
        self,
        seed_table: str,
        seed_pipeline: str | None,
    ) -> tuple[pl.DataFrame, int, str | None]:
        """Read and optionally qualify seed DataFrame."""
        self._logger.info("Reading seed table", table=seed_table)
        seed_df = await self._read_silver_table(seed_table)
        records_from_seed = len(seed_df)

        effective_seed_pipeline = seed_pipeline or self._infer_pipeline_from_table(
            seed_table
        )
        if not effective_seed_pipeline:
            return seed_df, records_from_seed, None

        self._logger.debug(
            "Using seed pipeline for column renaming",
            seed_pipeline=effective_seed_pipeline,
        )
        seed_df = self._renamer.rename_dataframe(
            seed_df,
            effective_seed_pipeline,
            exclude_join_keys=False,
            field_aliases=self._get_field_aliases(effective_seed_pipeline),
        )
        self._logger.info(
            "Renamed seed columns to qualified format",
            pipeline=effective_seed_pipeline,
            qualified_count=len(
                [
                    col
                    for col in seed_df.columns
                    if "." in col and not col.startswith("_")
                ]
            ),
        )
        return seed_df, records_from_seed, effective_seed_pipeline

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load only successful enricher silver tables."""
        enricher_dfs: dict[str, pl.DataFrame] = {}
        sources: list[str] = []

        for enricher in enrichers:
            result = enrichment_results.get(enricher.pipeline)
            if result is None or not result.is_success:
                continue

            enricher_table = enricher.silver_table or self._infer_silver_table(
                enricher.pipeline
            )
            self._logger.info(
                "Reading enricher table",
                enricher=enricher.pipeline,
                table=enricher_table,
            )

            try:
                enricher_df = await self._read_silver_table(enricher_table)
            except _MERGE_READ_ERRORS as error:
                self._logger.warning(
                    "Failed to read enricher table",
                    enricher=enricher.pipeline,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                continue
            except BioETLError as error:
                self._logger.warning(
                    "Failed to read enricher table",
                    enricher=enricher.pipeline,
                    error=str(error),
                    error_type=type(error).__name__,
                    reason_code="unexpected_bioetl_error",
                )
                continue

            enricher_dfs[enricher.pipeline] = enricher_df
            sources.append(enricher.pipeline)

        return enricher_dfs, sources

    async def _load_dependency_dataframes(
        self,
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load only successful dependency silver tables."""
        if not dependencies or not dependency_results:
            return {}, []

        dependency_dfs: dict[str, pl.DataFrame] = {}
        sources: list[str] = []

        for dep in dependencies:
            dep_result = dependency_results.get(dep.pipeline)
            if dep_result is None or not dep_result.is_success or not dep.silver_table:
                continue

            self._logger.info(
                "Reading dependency table",
                dependency=dep.pipeline,
                table=dep.silver_table,
            )

            try:
                dep_df = await self._read_silver_table(dep.silver_table)
            except _MERGE_READ_ERRORS as error:
                self._logger.warning(
                    "Failed to read dependency table",
                    dependency=dep.pipeline,
                    error=str(error),
                    error_type=type(error).__name__,
                )
                continue
            except BioETLError as error:
                self._logger.warning(
                    "Failed to read dependency table",
                    dependency=dep.pipeline,
                    error=str(error),
                    error_type=type(error).__name__,
                    reason_code="unexpected_bioetl_error",
                )
                continue

            dependency_dfs[dep.pipeline] = dep_df
            sources.append(dep.pipeline)

        return dependency_dfs, sources

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
        return validated_df, cv_stats, quarantine_payloads

    @staticmethod
    def _extract_quarantine_payloads(df: pl.DataFrame) -> list[dict[str, object]]:
        """Extract quarantine row payloads from _cv_quarantine marker column."""
        import polars as pl

        if "_cv_quarantine" not in df.columns:
            return []

        quarantine_df = df.filter(pl.col("_cv_quarantine"))
        if len(quarantine_df) == 0:
            return []

        return quarantine_df.to_dicts()

    async def _write_outputs(
        self,
        df: pl.DataFrame,
        run_id: str,
        sources_used: list[str],
    ) -> None:
        """Write final merged dataset to Silver and Gold outputs."""
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=len(df),
        )
        await self._write_merged_silver(df, run_id=run_id, sources_used=sources_used)

        self._logger.info(
            "Writing merged Gold table",
            path=self._config.output_gold_path,
            records=len(df),
        )
        await self._write_merged_gold(df, run_id=run_id, sources_used=sources_used)

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

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table from DeltaReaderPort or StoragePort fallback."""
        import polars as pl

        if self._delta_reader is not None:
            arrow_table = await self._delta_reader.read_table(path)
            result = pl.from_arrow(arrow_table)
            if isinstance(result, pl.Series):
                return result.to_frame()
            return result

        table_name = _path_to_table_name_local(path)
        records = await self._storage.read_silver(table_name)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)


__all__ = ["MergeIOMixin"]
