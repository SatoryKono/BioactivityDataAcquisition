"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.deduplication import EnricherDeduplicator
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.registry.field_aliases import get_alias_map_for_provider

JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]

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


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Find and strip layer prefix (handles both relative and absolute paths)
    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            # Take everything after the layer prefix
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


class MergeService:
    """Merges enriched data with conflict resolution and lineage tracking."""

    # Join keys that require case-insensitive matching (normalized to lowercase)
    # DOI: Different providers may store in different cases (10.1038/NATURE vs 10.1038/nature)
    # PMID: Typically numeric but may have inconsistent formatting
    _NORMALIZE_JOIN_KEYS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})

    # System columns to drop from enrichers before join
    # These are ETL metadata columns that should only come from seed
    # Prevents duplicate columns like _dq_error.A, _dq_error.B after merge
    _SYSTEM_COLUMNS_TO_DROP: frozenset[str] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",  # Data source identifier (e.g., "chembl", "crossref")
        }
    )

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidator | None = None,
    ) -> None:
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._deduplicator = EnricherDeduplicator(logger)
        self._aggregator = EnricherAggregator(logger)
        self._renamer = ColumnRenamer(logger)
        # Pass column_groups from config if available for YAML-based ordering
        self._orderer = ColumnOrderer(
            logger,
            column_groups=merge_config.column_groups
            if merge_config.column_groups
            else None,
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
        """Merge seed, dependency, and enricher data into unified output.

        Args:
            seed_table: Path to seed Silver table (e.g., "silver/chembl/publication").
            enrichers: Sequence of enricher configurations.
            enrichment_results: Results from enricher execution.
            run_id: Composite pipeline run ID.
            seed_pipeline: Seed pipeline name (e.g., "chembl_publication").
                If None, will be inferred from seed_table path.
                Used for intelligent column renaming during merge.
            dependencies: Sequence of dependency configurations (optional).
            dependency_results: Results from dependency execution (optional).

        Returns:
            MergeResult with statistics and output paths.
        """
        started_at = datetime.now(tz=UTC)

        # Step 1: Read seed data
        self._logger.info(
            "Reading seed table",
            table=seed_table,
        )
        seed_df = await self._read_silver_table(seed_table)
        records_from_seed = len(seed_df)

        # Determine effective seed pipeline name
        # Priority: explicit parameter > inferred from path
        effective_seed_pipeline = seed_pipeline or self._infer_pipeline_from_table(
            seed_table
        )

        # Rename seed columns to qualified format: {provider}.{entity}.{field}
        # Including join keys (doi, pmid, pmc_id) for full traceability
        if effective_seed_pipeline:
            self._logger.debug(
                "Using seed pipeline for column renaming",
                seed_pipeline=effective_seed_pipeline,
            )
            seed_df = self._renamer.rename_dataframe(
                seed_df,
                effective_seed_pipeline,
                exclude_join_keys=False,  # Rename ALL columns including join keys
                field_aliases=self._get_field_aliases(effective_seed_pipeline),
            )
            self._logger.info(
                "Renamed seed columns to qualified format",
                pipeline=effective_seed_pipeline,
                qualified_count=len(
                    [c for c in seed_df.columns if "." in c and not c.startswith("_")]
                ),
            )

        # Track sources used
        sources_used = ["seed"]
        enricher_dfs: dict[str, pl.DataFrame] = {}

        # Step 2: Read successful enricher tables
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
                enricher_dfs[enricher.pipeline] = enricher_df
                sources_used.append(enricher.pipeline)
            except Exception as e:
                self._logger.warning(
                    "Failed to read enricher table",
                    enricher=enricher.pipeline,
                    error=str(e),
                )

        # Step 2b: Read successful dependency tables
        dependency_dfs: dict[str, pl.DataFrame] = {}
        if dependencies and dependency_results:
            for dep in dependencies:
                dep_result = dependency_results.get(dep.pipeline)
                if dep_result is None or not dep_result.is_success:
                    continue

                dep_table = dep.silver_table
                if not dep_table:
                    continue

                self._logger.info(
                    "Reading dependency table",
                    dependency=dep.pipeline,
                    table=dep_table,
                )

                try:
                    dep_df = await self._read_silver_table(dep_table)
                    dependency_dfs[dep.pipeline] = dep_df
                    sources_used.append(dep.pipeline)
                except Exception as e:
                    self._logger.warning(
                        "Failed to read dependency table",
                        dependency=dep.pipeline,
                        error=str(e),
                    )

        # Step 3: Apply joins with intelligent column renaming
        merged_df = await self._apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        # Step 3b: Apply dependency joins (if any)
        if dependencies and dependency_dfs:
            merged_df = await self._apply_dependency_joins(
                merged_df=merged_df,
                dependency_dfs=dependency_dfs,
                dependencies=[d for d in dependencies if d.pipeline in dependency_dfs],
                seed_pipeline=effective_seed_pipeline,
            )
            self._logger.info(
                "Applied dependency joins",
                dependencies_joined=len(dependency_dfs),
                total_columns=len(merged_df.columns),
            )

        # Step 3c: Cross-validate seed vs enricher fields (pre-merge check)
        cv_stats: CrossValidationStats | None = None
        quarantine_payloads: list[dict[str, object]] = []
        if self._cross_validator is not None:
            enricher_pipelines_joined = [
                e.pipeline for e in enrichers if e.pipeline in enricher_dfs
            ]
            if enricher_pipelines_joined and effective_seed_pipeline:
                merged_df, cv_stats = self._cross_validator.validate(
                    merged_df,
                    enricher_pipelines_joined,
                    effective_seed_pipeline,
                )
                # Extract quarantine payloads from _cv_quarantine column
                if "_cv_quarantine" in merged_df.columns:
                    import polars as pl

                    q_df = merged_df.filter(pl.col("_cv_quarantine"))
                    if len(q_df) > 0:
                        quarantine_payloads = q_df.to_dicts()

        # Step 4: Resolve conflicts
        merged_df = self._resolve_conflicts(
            df=merged_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

        # Step 5: Add lineage metadata
        merged_df = self._add_lineage(
            df=merged_df,
            enrichment_results=enrichment_results,
            run_id=run_id,
            sources_used=sources_used,
            dependency_results=dependency_results,
        )

        # Step 5b: Drop excluded fields from merged output
        merged_df = self._drop_excluded_fields(merged_df)

        # Step 6: Order columns by semantic groups
        merged_df = self._orderer.order_columns(merged_df)
        self._logger.info(
            "Ordered columns by semantic groups",
            total_columns=len(merged_df.columns),
        )

        # Calculate statistics before writing
        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(
            merged_df, enrichers, effective_seed_pipeline
        )

        # Step 7: Write to Silver via StoragePort
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=records_merged,
        )
        await self._write_merged_silver(
            merged_df, run_id=run_id, sources_used=sources_used
        )

        # Step 8: Write to Gold via StoragePort
        self._logger.info(
            "Writing merged Gold table",
            path=self._config.output_gold_path,
            records=records_merged,
        )
        await self._write_merged_gold(
            merged_df, run_id=run_id, sources_used=sources_used
        )

        completed_at = datetime.now(tz=UTC)
        duration = (completed_at - started_at).total_seconds()

        self._logger.info(
            "Merge completed",
            records_merged=records_merged,
            sources_used=sources_used,
            duration_seconds=duration,
        )

        return MergeResult(
            records_merged=records_merged,
            records_from_seed=records_from_seed,
            records_enriched=records_enriched,
            records_fully_enriched=self._count_fully_enriched(merged_df, enrichers),
            sources_used=tuple(sources_used),
            field_coverage=self._calculate_field_coverage(merged_df),
            duration_seconds=duration,
            output_silver_path=self._config.output_silver_path,
            output_gold_path=self._config.output_gold_path,
            cross_validation_stats=cv_stats,
            quarantine_payloads=tuple(quarantine_payloads),
        )

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table.

        Uses DeltaReaderPort when configured (actual operation),
        or StoragePort when delta_reader is not set (for testing with mocks).

        Args:
            path: Table path like "silver/chembl/activity".

        Returns:
            Polars DataFrame with table contents.
        """
        import polars as pl

        # Use DeltaReaderPort when configured
        if self._delta_reader is not None:
            arrow_table = await self._delta_reader.read_table(path)
            result = pl.from_arrow(arrow_table)
            # from_arrow may return Series for single-column tables
            if isinstance(result, pl.Series):
                return result.to_frame()
            return result

        # Fall back to StoragePort (for testing with mocks)
        table_name = _path_to_table_name(path)
        records = await self._storage.read_silver(table_name)
        if not records:
            return pl.DataFrame()
        return pl.DataFrame(records)

    def _coerce_null_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Coerce Null-typed columns to String for Delta Lake compatibility.

        Delta Lake doesn't support Null type, so columns with all nulls
        (which Polars infers as Null type) must be cast to a concrete type.

        Args:
            df: DataFrame that may have Null-typed columns.

        Returns:
            DataFrame with Null columns cast to String.
        """
        import polars as pl

        null_cols = [col for col in df.columns if df[col].dtype == pl.Null]
        if null_cols:
            self._logger.debug(
                "Coercing null columns to String",
                columns=null_cols,
            )
            df = df.with_columns([pl.col(col).cast(pl.String) for col in null_cols])
        return df

    async def _write_merged_silver(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Silver layer via StoragePort.

        Args:
            df: Polars DataFrame to write.
            run_id: Composite run ID for metadata tracking.
            sources_used: List of source pipelines used in merge.
        """
        # Coerce null columns for Delta Lake compatibility
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
        """Write merged data to Gold layer via StoragePort.

        When a FieldGroupRegistry is configured, trash-group columns are
        excluded from the Gold output.

        Args:
            df: Polars DataFrame to write.
            run_id: Composite run ID for metadata tracking.
            sources_used: List of source pipelines used in merge.
        """
        # Filter out trash columns when field group registry is available
        if self._field_group_registry is not None:
            trash_cols = self._field_group_registry.get_trash_columns(df.columns)
            if trash_cols:
                self._logger.info(
                    "Filtering trash columns from Gold output",
                    trash_count=len(trash_cols),
                    trash_columns=trash_cols[:10],  # Log first 10 for brevity
                )
                df = df.drop(trash_cols)

        # Coerce null columns for Delta Lake compatibility
        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_gold_path)
        records = df.to_dicts()
        await self._storage.write_gold_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=True,
        )

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        # Convention: pipeline_name is "{provider}_{entity}"
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from Silver table path.

        Converts "silver/chembl/publication" → "chembl_publication".
        """
        # Check if path contains a recognized layer prefix
        normalized = table_path.replace("\\", "/")
        has_layer = any(
            layer in normalized for layer in ("silver/", "gold/", "bronze/")
        )
        if not has_layer:
            return None

        table_name = _path_to_table_name(table_path)
        # table_name is now like "chembl/publication"
        parts = table_name.split("/")
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1]}"
        return None

    def _find_join_key_column(
        self, key: str, columns: list[str], pipeline: str | None = None
    ) -> str | None:
        """Find column name for a join key (qualified or unqualified)."""
        if pipeline:
            try:
                provider, entity = self._parse_pipeline_name(pipeline)
                qualified = f"{provider}.{entity}.{key}"
                if qualified in columns:
                    return qualified
            except ValueError:
                pass
        if key in columns:
            return key
        return next((c for c in columns if c.endswith(f".{key}")), None)

    def _normalize_join_key_columns(
        self, df: pl.DataFrame, join_keys: list[str], pipeline: str | None = None
    ) -> pl.DataFrame:
        """Normalize join key columns to lowercase for case-insensitive matching."""
        import polars as pl

        cols = df.columns
        normalize = [
            c
            for key in join_keys
            if key in self._NORMALIZE_JOIN_KEYS
            for c in [self._find_join_key_column(key, cols, pipeline)]
            if c
        ]
        if not normalize:
            return df
        return df.with_columns(
            [pl.col(c).str.to_lowercase().alias(c) for c in normalize]
        )

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity) tuple."""
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return (parts[0], parts[1])

    def _get_field_aliases(self, pipeline: str) -> dict[str, str] | None:
        """Get field alias map for a pipeline's provider.

        Looks up the provider from the pipeline name and returns a mapping
        of provider-specific field names to canonical names. Returns None
        if the provider has no aliases (all fields already canonical).

        Args:
            pipeline: Pipeline name in format 'provider_entity'.

        Returns:
            Dict mapping provider field names to canonical names,
            or None if no aliases exist for the provider.
        """
        try:
            provider, _entity = self._parse_pipeline_name(pipeline)
        except ValueError:
            return None
        alias_map = get_alias_map_for_provider(provider)
        return alias_map if alias_map else None

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column (x.y.z → z)."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]
        return column

    def _find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Find next available A/B/C/... suffix for a conflicting column."""
        # Generate suffixes: A, B, C, ..., Z, AA, AB, ...
        suffix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        # Try single letters first
        for char in suffix_chars:
            candidate = f"{base_col}.{char}"
            if candidate not in existing_cols:
                return char

        # Try double letters (AA, AB, ..., ZZ)
        for first in suffix_chars:
            for second in suffix_chars:
                suffix = f"{first}{second}"
                candidate = f"{base_col}.{suffix}"
                if candidate not in existing_cols:
                    return suffix

        # Fallback (should never reach here with 702 possible suffixes)
        raise ValueError(f"Exhausted all suffixes for column '{base_col}'")

    def _detect_and_resolve_conflicts(
        self,
        seed_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_keys: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Detect and resolve column name conflicts between seed and enricher.

        Keeps seed columns unchanged, adds .A/.B suffixes to enricher columns.
        Join keys are excluded from conflict resolution.
        """
        seed_cols = set(seed_df.columns)
        enricher_cols = set(enricher_df.columns)

        # Find conflicts (excluding join keys)
        conflicts = (seed_cols & enricher_cols) - join_keys

        if not conflicts:
            return seed_df, enricher_df

        # Build rename map for enricher columns only
        # Use incremental suffixes, checking existing columns
        enricher_rename = {}
        for col in conflicts:
            suffix = self._find_next_suffix(col, seed_cols)
            enricher_rename[col] = f"{col}.{suffix}"

        self._logger.warning(
            "Column name conflicts detected after prefixing",
            conflicts=list(conflicts),
            resolution=f"Renaming enricher columns: {enricher_rename}",
        )

        # Seed columns remain unchanged, only enricher gets renamed
        return seed_df, enricher_df.rename(enricher_rename)

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply join strategy with qualified column renaming.

        Renames enricher columns to {provider}.{entity}.{field} format,
        normalizes join keys to lowercase, and resolves conflicts with .A/.B suffixes.
        """
        merged = seed_df

        for enricher in enrichers:
            if enricher.pipeline not in enricher_dfs:
                continue

            enricher_df = enricher_dfs[enricher.pipeline]
            join_keys_list = list(enricher.join_keys)

            # Primary key is the FIRST join key - used for actual join
            # Secondary keys are fallbacks but NOT used in join operation
            primary_key = join_keys_list[0]

            # Apply aggregation for MANY_TO_ONE enrichers BEFORE deduplication
            # This converts 1:M relationships to 1:1
            if enricher.is_many_to_one and enricher.aggregation is not None:
                enricher_df = self._aggregator.aggregate(
                    enricher_df,
                    enricher.aggregation,
                    enricher.pipeline,
                )

            # Deduplicate enricher before join to prevent fan-out
            enricher_df = self._deduplicator.deduplicate(
                enricher_df=enricher_df,
                join_keys=join_keys_list,
                enricher_name=enricher.pipeline,
            )

            # Normalize join key columns for case-insensitive matching
            # This ensures DOIs like "10.1038/NATURE" match "10.1038/nature"
            # For merged (seed), columns are already qualified (chembl.publication.doi)
            # For enricher, columns are still unqualified at this point
            merged = self._normalize_join_key_columns(
                merged, join_keys_list, pipeline=seed_pipeline
            )
            enricher_df = self._normalize_join_key_columns(
                enricher_df,
                join_keys_list,
                pipeline=None,  # Still unqualified
            )

            # Rename enricher columns to qualified format: {provider}.{entity}.{field}
            # Including join keys for full traceability
            # Field aliases normalize provider-specific names to canonical names
            enricher_df = self._renamer.rename_dataframe(
                enricher_df,
                enricher.pipeline,
                exclude_join_keys=False,  # Rename ALL columns including join keys
                field_aliases=self._get_field_aliases(enricher.pipeline),
            )

            self._logger.debug(
                "Renamed enricher columns to qualified format",
                enricher=enricher.pipeline,
                qualified_count=len(
                    [
                        c
                        for c in enricher_df.columns
                        if "." in c and not c.startswith("_")
                    ]
                ),
            )

            # Drop system columns from enricher to prevent duplicates like _dq_error.A
            # System columns should only come from seed (ETL metadata)
            enricher_df = self._drop_system_columns(enricher_df)

            # Calculate qualified join key names for both seed and enricher
            seed_join_key, enricher_join_key, seed_join_key_qualified = (
                self._resolve_join_key_names(
                    primary_key, seed_pipeline, enricher.pipeline, merged.columns
                )
            )

            # Detect and resolve remaining conflicts
            # Exclude both seed and enricher join keys from conflict detection
            join_key_set = {seed_join_key, enricher_join_key}
            if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
                join_key_set.add(seed_join_key_qualified)
            merged, enricher_df = self._detect_and_resolve_conflicts(
                merged, enricher_df, join_key_set
            )

            # Apply join using shared helper
            merged = self._execute_polars_join(
                merged, enricher_df, seed_join_key, enricher_join_key, enricher.pipeline
            )

        return merged

    def _execute_polars_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_key: str,
        right_key: str,
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute a Polars join with temp column handling and type coercion."""
        import polars as pl

        how = self._get_polars_join_type()

        if left_key not in left_df.columns or right_key not in right_df.columns:
            self._logger.warning(
                "Join skipped: key not found in columns",
                pipeline=pipeline_name,
                left_key=left_key,
                right_key=right_key,
                left_columns=left_df.columns
                if left_key not in left_df.columns
                else None,
                right_columns=right_df.columns
                if right_key not in right_df.columns
                else None,
            )
            return left_df

        # Coerce join keys to String to handle int64/float64 mismatches (e.g. nullable IDs)
        # This is the safest way to join IDs from different sources.
        # We also strip '.0' from the end of stringified floats to ensure '4044.0' matches '4044'.
        if left_df[left_key].dtype != right_df[right_key].dtype:
            self._logger.debug(
                "Coercing join keys to String due to type mismatch",
                pipeline=pipeline_name,
                left_key=left_key,
                left_type=str(left_df[left_key].dtype),
                right_key=right_key,
                right_type=str(right_df[right_key].dtype),
            )
            left_df = left_df.with_columns(
                pl.col(left_key).cast(pl.String).str.replace(r"\.0$", "", literal=False)
            )
            right_df = right_df.with_columns(
                pl.col(right_key)
                .cast(pl.String)
                .str.replace(r"\.0$", "", literal=False)
            )

        if left_key != right_key:
            # Use temp column to preserve qualified join key in right_df
            temp_join_col = f"__temp_join_{pipeline_name}"
            right_df = right_df.with_columns(pl.col(right_key).alias(temp_join_col))
            return left_df.join(
                right_df,
                left_on=left_key,
                right_on=temp_join_col,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        return left_df.join(
            right_df,
            left_on=left_key,
            right_on=right_key,
            how=how,
            suffix=f"_{pipeline_name}",
        )

    async def _apply_dependency_joins(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply joins for dependency tables.

        Dependencies use 1:1 cardinality with single or composite join keys.
        Columns are renamed to {provider}.{entity}.{field} format.
        """
        result = merged_df

        for dep in dependencies:
            if dep.pipeline not in dependency_dfs:
                continue

            dep_df = dependency_dfs[dep.pipeline]

            # Multi-field filter dependencies use composite key join
            if dep.is_multi_field_filter:
                result = self._apply_composite_key_dependency_join(
                    result, dep_df, dep, seed_pipeline
                )
                continue

            join_keys_list = list(dep.join_keys)
            primary_key = join_keys_list[0]

            # For dependencies with filter_field, use it for right-side operations
            # (e.g., protein_classification_id -> protein_class_id)
            right_key = dep.filter_field if dep.filter_field else primary_key
            right_keys_list = [right_key] if dep.filter_field else join_keys_list

            # Deduplicate dependency before join to prevent fan-out
            dep_df = self._deduplicator.deduplicate(
                enricher_df=dep_df,
                join_keys=right_keys_list,  # Use right-side key for dedup
                enricher_name=dep.pipeline,
            )

            # Normalize join key columns for case-insensitive matching
            result = self._normalize_join_key_columns(
                result, join_keys_list, pipeline=seed_pipeline
            )
            dep_df = self._normalize_join_key_columns(
                dep_df,
                right_keys_list,
                pipeline=None,  # Use right-side key
            )

            # Rename dependency columns to qualified format: {provider}.{entity}.{field}
            dep_df = self._renamer.rename_dataframe(
                dep_df,
                dep.pipeline,
                exclude_join_keys=False,
                field_aliases=self._get_field_aliases(dep.pipeline),
            )

            self._logger.debug(
                "Renamed dependency columns to qualified format",
                dependency=dep.pipeline,
                qualified_count=len(
                    [c for c in dep_df.columns if "." in c and not c.startswith("_")]
                ),
            )

            # Drop system columns from dependency to prevent duplicates
            dep_df = self._drop_system_columns(dep_df)

            # Calculate qualified join key names
            # For chained dependencies, use key_source pipeline for left-side key resolution
            left_pipeline = (
                dep.key_source
                if dep.key_source and dep.key_source != "seed"
                else seed_pipeline
            )

            # right_key already defined above for dedup/normalize

            seed_join_key, dep_join_key, seed_join_key_qualified = (
                self._resolve_join_key_names_asymmetric(
                    left_key=primary_key,
                    right_key=right_key,
                    left_pipeline=left_pipeline,
                    right_pipeline=dep.pipeline,
                    merged_columns=result.columns,
                )
            )

            # Detect and resolve conflicts
            join_key_set = {seed_join_key, dep_join_key}
            if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
                join_key_set.add(seed_join_key_qualified)
            result, dep_df = self._detect_and_resolve_conflicts(
                result, dep_df, join_key_set
            )

            # Apply join using shared helper
            result = self._execute_polars_join(
                result, dep_df, seed_join_key, dep_join_key, dep.pipeline
            )

            self._logger.debug(
                "Joined dependency",
                dependency=dep.pipeline,
                seed_join_key=seed_join_key,
                dep_join_key=dep_join_key,
                result_rows=len(result),
            )

        return result

    def _resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve qualified join key names for composite key join.

        Args:
            join_keys_list: Raw join key names.
            left_pipeline: Pipeline name for left-side key resolution.
            right_pipeline: Pipeline name for right-side key resolution.
            merged_columns: Available columns in the merged DataFrame.

        Returns:
            Tuple of (left_keys, right_keys, all_join_key_set).
        """
        left_keys: list[str] = []
        right_keys: list[str] = []
        all_join_key_set: set[str] = set()

        for key in join_keys_list:
            seed_key, dep_key, seed_key_qualified = (
                self._resolve_join_key_names_asymmetric(
                    left_key=key,
                    right_key=key,
                    left_pipeline=left_pipeline,
                    right_pipeline=right_pipeline,
                    merged_columns=merged_columns,
                )
            )
            left_keys.append(seed_key)
            right_keys.append(dep_key)
            all_join_key_set.add(seed_key)
            all_join_key_set.add(dep_key)
            if seed_key_qualified and seed_key_qualified != seed_key:
                all_join_key_set.add(seed_key_qualified)

        return left_keys, right_keys, all_join_key_set

    def _execute_composite_key_join(
        self,
        left_df: pl.DataFrame,
        right_df: pl.DataFrame,
        left_keys: list[str],
        right_keys: list[str],
        pipeline_name: str,
    ) -> pl.DataFrame:
        """Execute a Polars join on multiple keys.

        Args:
            left_df: Left DataFrame.
            right_df: Right DataFrame.
            left_keys: Column names in left_df for join.
            right_keys: Column names in right_df for join.
            pipeline_name: Pipeline name for suffix.

        Returns:
            Joined DataFrame.
        """
        import polars as pl

        how = self._get_polars_join_type()

        if left_keys == right_keys:
            return left_df.join(
                right_df,
                on=left_keys,
                how=how,
                suffix=f"_{pipeline_name}",
            )

        # Different column names — use temp columns for right-side
        temp_cols = []
        for lk, rk in zip(left_keys, right_keys, strict=True):
            if lk != rk:
                temp_col = f"__temp_join_{pipeline_name}_{rk}"
                right_df = right_df.with_columns(pl.col(rk).alias(temp_col))
                temp_cols.append(temp_col)
            else:
                temp_cols.append(rk)

        return left_df.join(
            right_df,
            left_on=left_keys,
            right_on=temp_cols,
            how=how,
            suffix=f"_{pipeline_name}",
        )

    def _apply_composite_key_dependency_join(
        self,
        merged_df: pl.DataFrame,
        dep_df: pl.DataFrame,
        dep: DependencyConfig,
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply composite key join for multi-field filter dependencies.

        Used when a dependency filters by multiple fields (e.g., compound_record
        filtered by both molecule_chembl_id and document_chembl_id). Joins on
        all join_keys simultaneously to produce precise 1:1 matches.

        Args:
            merged_df: DataFrame with seed data.
            dep_df: Dependency DataFrame to join.
            dep: Dependency configuration with multiple filter_fields.
            seed_pipeline: Seed pipeline name for join key resolution.

        Returns:
            DataFrame with dependency joined on composite key.
        """
        join_keys_list = list(dep.join_keys)

        # Deduplicate on all join keys (composite dedup)
        dep_df = self._deduplicator.deduplicate(
            enricher_df=dep_df,
            join_keys=join_keys_list,
            enricher_name=dep.pipeline,
        )

        # Normalize join key columns
        merged_df = self._normalize_join_key_columns(
            merged_df, join_keys_list, pipeline=seed_pipeline
        )
        dep_df = self._normalize_join_key_columns(dep_df, join_keys_list, pipeline=None)

        # Rename dependency columns to qualified format
        dep_df = self._renamer.rename_dataframe(
            dep_df,
            dep.pipeline,
            exclude_join_keys=False,
            field_aliases=self._get_field_aliases(dep.pipeline),
        )

        # Drop system columns from dependency
        dep_df = self._drop_system_columns(dep_df)

        # Resolve qualified join key names for each key
        left_pipeline = (
            dep.key_source
            if dep.key_source and dep.key_source != "seed"
            else seed_pipeline
        )
        left_keys, right_keys, all_join_key_set = self._resolve_composite_join_keys(
            join_keys_list, left_pipeline, dep.pipeline, merged_df.columns
        )

        # Detect and resolve conflicts (excluding all join keys)
        merged_df, dep_df = self._detect_and_resolve_conflicts(
            merged_df, dep_df, all_join_key_set
        )

        # Verify all join keys exist
        missing_left = [k for k in left_keys if k not in merged_df.columns]
        missing_right = [k for k in right_keys if k not in dep_df.columns]
        if missing_left or missing_right:
            self._logger.warning(
                "Composite key join skipped: missing columns",
                dependency=dep.pipeline,
                missing_left=missing_left,
                missing_right=missing_right,
            )
            return merged_df

        result = self._execute_composite_key_join(
            merged_df, dep_df, left_keys, right_keys, dep.pipeline
        )

        self._logger.debug(
            "Joined dependency with composite key",
            dependency=dep.pipeline,
            left_keys=left_keys,
            right_keys=right_keys,
            result_rows=len(result),
        )

        return result

    def _get_polars_join_type(self) -> JoinHow:
        """Convert MergeStrategy to Polars join type."""
        match self._config.strategy:
            case MergeStrategy.LEFT_OUTER:
                return "left"
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"

    def _drop_system_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop system columns from DataFrame to prevent duplicates after join.

        System columns (_dq_error, _run_id, etc.) should only come from the seed.
        Dropping them from enrichers prevents columns like _dq_error.A, _dq_error.B
        after multiple joins.

        Args:
            df: Enricher DataFrame.

        Returns:
            DataFrame with system columns removed.
        """
        columns_to_drop = [
            col for col in df.columns if col in self._SYSTEM_COLUMNS_TO_DROP
        ]

        if columns_to_drop:
            self._logger.debug(
                "Dropping system columns from enricher",
                columns=columns_to_drop,
            )
            return df.drop(columns_to_drop)

        return df

    def _resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names for seed and enricher.

        Args:
            primary_key: Unqualified join key name.
            seed_pipeline: Seed pipeline name for qualification.
            enricher_pipeline: Enricher pipeline name for qualification.
            merged_columns: Current merged DataFrame columns.

        Returns:
            Tuple of (seed_join_key, enricher_join_key, seed_join_key_qualified).
        """
        seed_join_key_qualified: str | None = None
        seed_join_key = primary_key

        if seed_pipeline is not None:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
                seed_join_key_qualified = f"{seed_provider}.{seed_entity}.{primary_key}"
                if seed_join_key_qualified in merged_columns:
                    seed_join_key = seed_join_key_qualified
            except ValueError:
                pass

        try:
            enricher_provider, enricher_entity = self._parse_pipeline_name(
                enricher_pipeline
            )
            enricher_join_key = f"{enricher_provider}.{enricher_entity}.{primary_key}"
        except ValueError:
            enricher_join_key = primary_key

        return seed_join_key, enricher_join_key, seed_join_key_qualified

    def _resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names with different keys for left/right.

        Used when join key has different names in source and target tables.
        E.g., protein_classification_id (in target_component) -> protein_class_id (in protein_class).

        Args:
            left_key: Unqualified join key name in left (merged) DataFrame.
            right_key: Unqualified join key name in right (dependency) DataFrame.
            left_pipeline: Pipeline name for left-side qualification (key_source or seed).
            right_pipeline: Pipeline name for right-side qualification.
            merged_columns: Current merged DataFrame columns.

        Returns:
            Tuple of (left_join_key, right_join_key, left_join_key_qualified).
        """
        left_join_key_qualified: str | None = None
        left_join_key = left_key

        # Resolve left-side key (from key_source or seed)
        if left_pipeline is not None:
            try:
                left_provider, left_entity = self._parse_pipeline_name(left_pipeline)
                left_join_key_qualified = f"{left_provider}.{left_entity}.{left_key}"
                if left_join_key_qualified in merged_columns:
                    left_join_key = left_join_key_qualified
            except ValueError:
                pass

        # Resolve right-side key (from dependency)
        try:
            right_provider, right_entity = self._parse_pipeline_name(right_pipeline)
            right_join_key = f"{right_provider}.{right_entity}.{right_key}"
        except ValueError:
            right_join_key = right_key

        return left_join_key, right_join_key, left_join_key_qualified

    def _get_enricher_prefix(
        self,
        enricher_pipeline: str,
        seed_pipeline: str | None = None,
    ) -> str:
        """Get column prefix for enricher.

        Returns {provider}.{entity}. format for qualified column matching.

        Args:
            enricher_pipeline: Enricher pipeline name.
            seed_pipeline: Unused, kept for backward compatibility.

        Returns:
            Prefix string WITH trailing dot: '{provider}.{entity}.'
        """
        try:
            provider, entity = self._parse_pipeline_name(enricher_pipeline)
            return f"{provider}.{entity}."
        except ValueError:
            # Fallback for non-standard pipeline names
            return f"{enricher_pipeline}_"

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from a prefixed column.

        Supports both:
        - New format: "crossref.publication.title" with prefix "crossref.publication." → "title"
        - Legacy format: "crossref_title" with prefix "crossref_" → "title"

        Args:
            column: Column name that may have a prefix.
            prefix: Prefix to strip (WITH trailing dot or underscore).

        Returns:
            Base column name if column starts with prefix, None otherwise.
        """
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
        """Apply conflict resolution based on configured strategy.

        Args:
            df: Merged DataFrame with prefixed columns.
            enricher_dfs: Original enricher DataFrames (for reference).
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with conflicts resolved.
        """
        # Skip coalescing if preserve_all_sources is enabled
        # This keeps all provider-qualified columns (e.g., chembl.publication.title,
        # crossref.publication.title) instead of merging them
        if self._config.preserve_all_sources:
            qualified_cols = [
                c for c in df.columns if "." in c and not c.startswith("_")
            ]
            self._logger.info(
                "Skipping conflict resolution - preserve_all_sources=True",
                qualified_columns=len(qualified_cols),
            )
            return df

        match self._config.conflict_resolution:
            case ConflictResolution.SEED_PRIORITY:
                return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)
            case ConflictResolution.ENRICHER_PRIORITY:
                return self._coalesce_prefer_enricher(df, enrichers, seed_pipeline)
            case ConflictResolution.COALESCE:
                return self._coalesce_first_non_null(df, enrichers, seed_pipeline)
            case ConflictResolution.EXPLICIT_RULES:
                return self._apply_explicit_rules(df, enrichers, seed_pipeline)
            case ConflictResolution.LATEST_TIMESTAMP:
                # Would require timestamp columns - fall back to seed
                return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)
            case _:
                return df

    def _can_coalesce(self, df: pl.DataFrame, col1: str, col2: str) -> bool:
        """Check if two columns can be coalesced (compatible types).

        Args:
            df: DataFrame containing the columns.
            col1: First column name.
            col2: Second column name.

        Returns:
            True if columns have compatible types for coalescing.
        """
        import polars as pl

        type1 = df[col1].dtype
        type2 = df[col2].dtype

        # Same type is always compatible
        if type1 == type2:
            return True

        # Null type is compatible with anything
        if type1 == pl.Null or type2 == pl.Null:
            return True

        # List types are incompatible with scalar types
        # Different scalar types may be compatible (Polars handles casting)
        return isinstance(type1, pl.List) == isinstance(type2, pl.List)

    def _coalesce_prefer_seed(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce preferring seed values.

        Groups columns by field name and coalesces within each group,
        with seed columns having priority.

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for identifying seed columns.

        Returns:
            DataFrame with coalesced columns.
        """
        import polars as pl

        result = df

        # Parse seed prefix for identification
        seed_prefix: str | None = None
        if seed_pipeline:
            try:
                provider, entity = self._parse_pipeline_name(seed_pipeline)
                seed_prefix = f"{provider}.{entity}."
            except ValueError:
                pass

        # Group columns by field name
        field_groups: dict[str, list[str]] = {}
        for col in result.columns:
            if col.startswith("_"):  # Skip system columns
                continue
            field = self._extract_field_from_qualified(col)
            if field not in field_groups:
                field_groups[field] = []
            field_groups[field].append(col)

        # Process each group with multiple columns
        for _field, columns in field_groups.items():
            if len(columns) <= 4:
                continue

            # Sort: seed columns first, then enrichers
            def sort_key(c: str) -> int:
                if seed_prefix and c.startswith(seed_prefix):
                    return 0  # Seed first
                return 1  # Enrichers after

            sorted_cols = sorted(columns, key=sort_key)

            # Filter compatible columns (same dtype)
            compatible_cols = [sorted_cols[0]]
            for col in sorted_cols[1:]:
                if self._can_coalesce(result, sorted_cols[0], col):
                    compatible_cols.append(col)

            if len(compatible_cols) > 1:
                # Coalesce into the first (seed) column
                target_col = compatible_cols[0]
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )
                # Drop non-target columns
                cols_to_drop = [c for c in compatible_cols[1:] if c in result.columns]
                if cols_to_drop:
                    result = result.drop(cols_to_drop)

        return result

    def _coalesce_prefer_enricher(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce preferring enricher values.

        Groups columns by field name and coalesces within each group,
        with enricher columns having priority over seed.

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for identifying seed columns.

        Returns:
            DataFrame with coalesced columns.
        """
        import polars as pl

        result = df

        seed_prefix: str | None = None
        if seed_pipeline:
            try:
                provider, entity = self._parse_pipeline_name(seed_pipeline)
                seed_prefix = f"{provider}.{entity}."
            except ValueError:
                pass

        field_groups: dict[str, list[str]] = {}
        for col in result.columns:
            if col.startswith("_"):
                continue
            field = self._extract_field_from_qualified(col)
            if field not in field_groups:
                field_groups[field] = []
            field_groups[field].append(col)

        for _field, columns in field_groups.items():
            if len(columns) <= 1:
                continue

            # Sort: enrichers first, seed last
            def sort_key(c: str) -> int:
                if seed_prefix and c.startswith(seed_prefix):
                    return 1  # Seed last
                return 0  # Enrichers first

            sorted_cols = sorted(columns, key=sort_key)

            compatible_cols = [sorted_cols[0]]
            for col in sorted_cols[1:]:
                if self._can_coalesce(result, sorted_cols[0], col):
                    compatible_cols.append(col)

            if len(compatible_cols) > 1:
                target_col = compatible_cols[0]
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )
                cols_to_drop = [c for c in compatible_cols[1:] if c in result.columns]
                if cols_to_drop:
                    result = result.drop(cols_to_drop)

        return result

    def _coalesce_first_non_null(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce taking first non-null value.

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with coalesced columns.
        """
        # Same as seed priority for now
        return self._coalesce_prefer_seed(df, enrichers, seed_pipeline)

    def _collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[EnricherConfig],
        available_columns: set[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Collect all columns for a field from all sources.

        Searches for qualified format ONLY:
        - Seed: {seed_provider}.{seed_entity}.{field}
        - Enrichers: {enricher_provider}.{enricher_entity}.{field}

        Legacy unqualified names are NOT searched (seed already renamed).

        Args:
            field: Base field name (e.g., 'title').
            enrichers: Enricher configurations.
            available_columns: Columns present in DataFrame.
            seed_pipeline: Seed pipeline name for qualified lookup.

        Returns:
            List of matching qualified column names.
        """
        columns: list[str] = []

        # 1. Seed qualified format: {seed_provider}.{seed_entity}.{field}
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

        # 2. Each enricher's qualified format: {provider}.{entity}.{field}
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
                # Fallback: legacy prefix format {pipeline}_{field}
                prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
                legacy_col = f"{prefix}{field}".rstrip(".")
                if legacy_col in available_columns and legacy_col not in columns:
                    columns.append(legacy_col)

        return columns

    def _order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Order columns by source priority for coalescing.

        Priority format in config:
        - 'seed' - refers to seed pipeline (resolved dynamically)
        - '{provider}' - matches {provider}.*.{field}
        - '{provider}.{entity}' - explicit match

        Args:
            field: Base field name.
            columns: Available column names for this field.
            priorities: Priority list from config (e.g., ['seed', 'crossref']).
            seed_pipeline: Seed pipeline for resolving 'seed' priority.

        Returns:
            Ordered list of columns by priority.
        """
        ordered_cols: list[str] = []
        columns_set = set(columns)

        # Parse seed for matching
        seed_provider: str | None = None
        seed_entity: str | None = None
        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
            except ValueError:
                pass

        for source in priorities:
            source_lower = source.lower()
            qualified: str | None = None

            # Handle 'seed' keyword - resolve to actual seed provider.entity
            if source_lower == "seed":
                if seed_provider and seed_entity:
                    qualified = f"{seed_provider}.{seed_entity}.{field}"

            # Handle explicit provider.entity format: 'crossref.publication'
            elif "." in source:
                parts = source.split(".", 1)
                provider, entity = parts[0].lower(), parts[1].lower()
                qualified = f"{provider}.{entity}.{field}"

            # Handle provider-only: find matching column
            else:
                provider = source_lower
                # Check if this provider matches seed
                if seed_provider and provider == seed_provider.lower():
                    if seed_entity:
                        qualified = f"{provider}.{seed_entity}.{field}"
                else:
                    # Try to find any column with this provider
                    for col in columns_set:
                        if col.startswith(f"{provider}.") and col.endswith(f".{field}"):
                            qualified = col
                            break

            if qualified and qualified in columns_set and qualified not in ordered_cols:
                ordered_cols.append(qualified)

        # Append remaining columns not in priority list (preserving discovery order)
        for col in columns:
            if col not in ordered_cols:
                ordered_cols.append(col)

        return ordered_cols

    def _filter_compatible_columns(
        self,
        df: pl.DataFrame,
        field: str,
        ordered_cols: list[str],
    ) -> tuple[list[str], list[str]]:
        """Filter columns to only those compatible for coalescing.

        Args:
            df: DataFrame containing the columns.
            field: Base field name for logging.
            ordered_cols: Ordered list of column names.

        Returns:
            Tuple of (compatible_columns, incompatible_columns).
        """
        if not ordered_cols:
            return [], []

        base_col = ordered_cols[0]
        compatible_cols = [base_col]
        incompatible_cols: list[str] = []

        for col in ordered_cols[1:]:
            if self._can_coalesce(df, base_col, col):
                compatible_cols.append(col)
            else:
                self._logger.debug(
                    "Skipping column with incompatible type in explicit rules",
                    field=field,
                    incompatible_col=col,
                    base_type=str(df[base_col].dtype),
                    col_type=str(df[col].dtype),
                )
                incompatible_cols.append(col)

        return compatible_cols, incompatible_cols

    def _apply_explicit_rules(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply explicit field priority rules.

        Coalesces columns by priority, handling type compatibility.

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with explicit rules applied.
        """
        import polars as pl

        result = df
        available_columns = set(df.columns)

        for field, priorities in self._config.field_priorities.items():
            columns = self._collect_field_columns(
                field, enrichers, available_columns, seed_pipeline
            )

            if len(columns) <= 1:
                continue

            ordered_cols = self._order_columns_by_priority(
                field, columns, priorities, seed_pipeline
            )

            if not ordered_cols:
                continue

            compatible_cols, _ = self._filter_compatible_columns(
                result, field, ordered_cols
            )

            # Coalesce compatible columns into the first (highest priority) column
            if len(compatible_cols) > 1:
                target_col = compatible_cols[
                    0
                ]  # Keep the first column name (qualified)
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )

            # Drop all non-target columns
            cols_to_drop = [col for col in compatible_cols[1:] if col in result.columns]
            if cols_to_drop:
                result = result.drop(cols_to_drop)

        return result

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

        # Build enrichment status dict (enrichers + dependencies)
        status_dict: dict[str, str] = {}
        if dependency_results:
            for name, dep_result in dependency_results.items():
                status_dict[name] = dep_result.status.value
        for name, enrich_result in enrichment_results.items():
            status_dict[name] = enrich_result.status.value

        # Add lineage columns
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
        """Count records with at least one enrichment.

        Counts records where at least one enricher-sourced column is non-null.
        Works with qualified column names ({provider}.{entity}.{field}).

        Args:
            df: Merged DataFrame with qualified columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name (for identifying seed columns).

        Returns:
            Count of records with at least one non-null enricher column.
        """
        import polars as pl

        enricher_cols: list[str] = []

        for enricher in enrichers:
            try:
                provider, entity = self._parse_pipeline_name(enricher.pipeline)
                prefix = f"{provider}.{entity}."
            except ValueError:
                prefix = f"{enricher.pipeline}_"

            enricher_cols.extend([c for c in df.columns if c.startswith(prefix)])

        if not enricher_cols:
            return 0

        # Count records where at least one enricher column is non-null
        any_enriched = pl.any_horizontal(
            [pl.col(c).is_not_null() for c in enricher_cols]
        )
        return len(df.filter(any_enriched))

    def _count_fully_enriched(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> int:
        """Count records with all required enrichments."""
        # Simplified implementation
        return 0

    def _calculate_field_coverage(self, df: pl.DataFrame) -> dict[str, float]:
        """Calculate percentage of non-null values per field."""
        if len(df) == 0:
            return {}

        coverage = {}
        for col in df.columns:
            if not col.startswith("_"):  # Skip metadata columns
                non_null = len(df.filter(df[col].is_not_null()))
                coverage[col] = non_null / len(df)

        return coverage
