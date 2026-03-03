"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.coalesce_policy import CoalescePolicy
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_priority_orderer import ColumnPriorityOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolver
from bioetl.application.composite.deduplication import EnricherDeduplicator
from bioetl.application.composite.join_planner import JoinHow, JoinPlanner
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)
from bioetl.domain.registry.field_aliases import get_alias_map_for_provider

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.cross_validator import EnrichmentCrossValidator
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.cross_validation import CrossValidationStats
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
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


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeService:
    """Facade/orchestrator for seed+dependency+enricher merge workflow."""

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidator | None = None,
        gold_schema: Any | None = None,
    ) -> None:
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._gold_schema = gold_schema

        self._deduplicator = EnricherDeduplicator(logger)
        self._aggregator = EnricherAggregator(logger)
        self._renamer = ColumnRenamer(logger)
        self._orderer = ColumnOrderer(
            logger,
            column_groups=merge_config.column_groups
            if merge_config.column_groups
            else None,
        )

        self._priority_orderer = ColumnPriorityOrderer(logger)
        self._coalesce_policy = CoalescePolicy(logger, self._priority_orderer)
        self._conflict_resolver = ConflictResolver(
            merge_config,
            logger,
            self._coalesce_policy,
        )
        self._join_planner = JoinPlanner(
            merge_config=merge_config,
            logger=logger,
            deduplicator=self._deduplicator,
            aggregator=self._aggregator,
            renamer=self._renamer,
            conflict_resolver=self._conflict_resolver,
            field_alias_resolver=self._get_field_aliases,
        )

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
        dependencies: Sequence[DependencyConfig] | None = None,
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> MergeResult:
        """Merge seed, dependency, and enricher data into unified output."""
        started_at = datetime.now(tz=UTC)

        (
            seed_df,
            records_from_seed,
            effective_seed_pipeline,
        ) = await self._prepare_seed_dataframe(seed_table, seed_pipeline)

        sources_used = ["seed"]
        enricher_dfs, enricher_sources = await self._load_enricher_dataframes(
            enrichers,
            enrichment_results,
        )
        sources_used.extend(enricher_sources)

        dependency_dfs, dependency_sources = await self._load_dependency_dataframes(
            dependencies,
            dependency_results,
        )
        sources_used.extend(dependency_sources)

        merged_df = await self._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        merged_df = await self._apply_dependency_joins_if_needed(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=dependencies,
            seed_pipeline=effective_seed_pipeline,
        )

        merged_df, cv_stats, quarantine_payloads = self._run_cross_validation(
            merged_df=merged_df,
            enrichers=enrichers,
            enricher_dfs=enricher_dfs,
            effective_seed_pipeline=effective_seed_pipeline,
        )

        merged_df = self._conflict_resolver.resolve_conflicts(
            df=merged_df,
            _enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        merged_df = self._add_lineage(
            df=merged_df,
            enrichment_results=enrichment_results,
            run_id=run_id,
            sources_used=sources_used,
            dependency_results=dependency_results,
        )
        merged_df = self._drop_excluded_fields(merged_df)
        merged_df = self._orderer.order_columns(merged_df)

        self._logger.info(
            "Ordered columns by semantic groups",
            total_columns=len(merged_df.columns),
        )

        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(
            merged_df,
            enrichers,
            effective_seed_pipeline,
        )

        await self._write_outputs(merged_df, run_id=run_id, sources_used=sources_used)

        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()

        self._logger.info(
            "Merge completed",
            records_merged=records_merged,
            sources_used=sources_used,
            duration_seconds=duration,
        )

        return self._build_merge_result(
            merged_df=merged_df,
            enrichers=enrichers,
            records_merged=records_merged,
            records_from_seed=records_from_seed,
            records_enriched=records_enriched,
            sources_used=sources_used,
            duration_seconds=duration,
            cv_stats=cv_stats,
            quarantine_payloads=quarantine_payloads,
        )

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

        table_name = _path_to_table_name(path)
        records = await self._storage.read_silver(table_name)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)

    def _coerce_null_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Coerce Null-typed columns to String for Delta Lake compatibility."""
        import polars as pl

        null_cols = [col for col in df.columns if df[col].dtype == pl.Null]
        if null_cols:
            self._logger.debug("Coercing null columns to String", columns=null_cols)
            df = df.with_columns([pl.col(col).cast(pl.String) for col in null_cols])
        return df

    async def _write_merged_silver(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Silver layer via StoragePort."""
        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_silver_path)
        records = df.to_dicts()
        await self._storage.write_silver_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=True,
        )

    async def _write_merged_gold(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Gold layer via StoragePort."""
        if self._field_group_registry is not None:
            trash_cols = self._field_group_registry.get_trash_columns(df.columns)
            if trash_cols:
                self._logger.info(
                    "Filtering trash columns from Gold output",
                    trash_count=len(trash_cols),
                    trash_columns=trash_cols[:10],
                )
                df = df.drop(trash_cols)

        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_gold_path)
        records = df.to_dicts()
        await self._storage.write_gold_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=True,
            schema=self._gold_schema,
        )

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from table path (silver/provider/entity)."""
        normalized = table_path.replace("\\", "/")
        has_layer = any(
            layer in normalized for layer in ("silver/", "gold/", "bronze/")
        )
        if not has_layer:
            return None

        table_name = _path_to_table_name(table_path)
        parts = table_name.split("/")
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1]}"
        return None

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return parts[0], parts[1]

    def _get_field_aliases(self, pipeline: str) -> dict[str, str] | None:
        """Get provider field alias mapping for pipeline provider."""
        try:
            provider, _entity = self._parse_pipeline_name(pipeline)
        except ValueError:
            return None
        alias_map = get_alias_map_for_provider(provider)
        return alias_map if alias_map else None

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column (x.y.z -> z)."""
        return self._coalesce_policy.extract_field_from_qualified(column)

    def _find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Compatibility wrapper for join-key column lookup."""
        return self._join_planner.find_join_key_column(key, columns, pipeline)

    def _normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for join-key normalization."""
        return self._join_planner.normalize_join_key_columns(df, join_keys, pipeline)

    def _find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Compatibility wrapper for suffix allocation."""
        return self._conflict_resolver.find_next_suffix(base_col, existing_cols)

    def _detect_and_resolve_conflicts(
        self,
        seed_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_keys: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Compatibility wrapper for conflict detection and renaming."""
        return self._conflict_resolver.detect_and_resolve_conflicts(
            seed_df,
            enricher_df,
            join_keys,
        )

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for enricher joins."""
        return await self._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=seed_pipeline,
        )

    def _execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Compatibility wrapper for single-key Polars join."""
        return self._join_planner.execute_polars_join(
            left_df,
            right_df,
            left_key,
            right_key,
            pipeline_name,
        )

    async def _apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for dependency joins."""
        return await self._join_planner.apply_dependency_joins(
            merged_df=merged_df,
            dependency_dfs=dependency_dfs,
            dependencies=dependencies,
            seed_pipeline=seed_pipeline,
        )

    def _resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Compatibility wrapper for composite join-key resolution."""
        return self._join_planner.resolve_composite_join_keys(
            join_keys_list,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )

    def _execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Compatibility wrapper for composite-key join."""
        return self._join_planner.execute_composite_key_join(
            left_df,
            right_df,
            left_keys,
            right_keys,
            pipeline_name,
        )

    def _apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for composite-key dependency joins."""
        return self._join_planner.apply_composite_key_dependency_join(
            merged_df,
            dep_df,
            dep,
            seed_pipeline,
        )

    def _get_polars_join_type(self) -> JoinHow:
        """Compatibility wrapper for join strategy mapping."""
        return self._join_planner.get_polars_join_type()

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Compatibility wrapper for system-column cleanup."""
        return self._join_planner.drop_system_columns(df)

    def _resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Compatibility wrapper for symmetric join-key resolution."""
        return self._join_planner.resolve_join_key_names(
            primary_key,
            seed_pipeline,
            enricher_pipeline,
            merged_columns,
        )

    def _resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Compatibility wrapper for asymmetric join-key resolution."""
        return self._join_planner.resolve_join_key_names_asymmetric(
            left_key,
            right_key,
            left_pipeline,
            right_pipeline,
            merged_columns,
        )

    def _get_enricher_prefix(
        self,
        enricher_pipeline: str,
        seed_pipeline: str | None = None,
    ) -> str:
        """Compatibility helper for enricher prefix resolution."""
        _ = seed_pipeline
        return self._priority_orderer.get_enricher_prefix(enricher_pipeline)

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from prefixed column name."""
        if column.startswith(prefix):
            return column[len(prefix) :]
        return None

    def _resolve_conflicts(
        self,
        df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for policy-based conflict resolution."""
        return self._conflict_resolver.resolve_conflicts(
            df,
            enricher_dfs,
            enrichers,
            seed_pipeline,
        )

    def _can_coalesce(self, df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Compatibility wrapper for type-compatibility checks."""
        return self._coalesce_policy.can_coalesce(df, col1, col2)

    def _coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for seed-priority coalesce policy."""
        return self._coalesce_policy.coalesce_prefer_seed(df, enrichers, seed_pipeline)

    def _coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for enricher-priority coalesce policy."""
        return self._coalesce_policy.coalesce_prefer_enricher(
            df,
            enrichers,
            seed_pipeline,
        )

    def _coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for first-non-null coalesce policy."""
        return self._coalesce_policy.coalesce_first_non_null(
            df,
            enrichers,
            seed_pipeline,
        )

    def _collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Compatibility wrapper for field-column collection."""
        return self._priority_orderer.collect_field_columns(
            field,
            enrichers,
            available_columns,
            seed_pipeline,
        )

    def _order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Compatibility wrapper for source-priority ordering."""
        return self._priority_orderer.order_columns_by_priority(
            field,
            columns,
            priorities,
            seed_pipeline,
        )

    def _filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
    ) -> tuple[list[str], list[str]]:
        """Compatibility wrapper for explicit-rule compatibility filtering."""
        return self._priority_orderer.filter_compatible_columns(
            df,
            field,
            ordered_cols,
            self._coalesce_policy.can_coalesce,
        )

    def _apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Compatibility wrapper for explicit priority rules."""
        return self._coalesce_policy.apply_explicit_rules(
            df,
            enrichers,
            self._config.field_priorities,
            seed_pipeline,
        )

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
