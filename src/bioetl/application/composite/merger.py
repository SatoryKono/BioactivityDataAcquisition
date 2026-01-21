"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from bioetl.domain.composite.result import EnrichmentResult, MergeResult
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross", "outer"]

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig, MergeConfig
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort, StoragePort


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix.

    Handles both relative and absolute paths:
    - "silver/chembl/activity" → "chembl/activity"
    - "data/output/silver/chembl/activity" → "chembl/activity"
    - "gold/composite/publication" → "composite/publication"
    - "data/output/gold/composite/publication" → "composite/publication"

    Args:
        path: Path containing a layer segment (silver/, gold/, bronze/).

    Returns:
        Table name with layer prefix stripped.
    """
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

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
    ) -> None:
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
    ) -> MergeResult:
        """Merge seed and enricher data into unified output."""
        started_at = datetime.now(tz=UTC)

        # Step 1: Read seed data
        self._logger.info(
            "Reading seed table",
            table=seed_table,
        )
        seed_df = await self._read_silver_table(seed_table)
        records_from_seed = len(seed_df)

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

        # Step 3: Apply joins
        merged_df = await self._apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
        )

        # Step 4: Resolve conflicts
        merged_df = self._resolve_conflicts(
            df=merged_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
        )

        # Step 5: Add lineage metadata
        merged_df = self._add_lineage(
            df=merged_df,
            enrichment_results=enrichment_results,
            run_id=run_id,
            sources_used=sources_used,
        )

        # Calculate statistics before writing
        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(merged_df, enrichers)

        # Step 6: Write to Silver via StoragePort
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=records_merged,
        )
        await self._write_merged_silver(
            merged_df, run_id=run_id, sources_used=sources_used
        )

        # Step 7: Write to Gold via StoragePort
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
        )

    async def _write_merged_gold(
        self,
        df: pl.DataFrame,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged data to Gold layer via StoragePort.

        Args:
            df: Polars DataFrame to write.
            run_id: Composite run ID for metadata tracking.
            sources_used: List of source pipelines used in merge.
        """
        # Coerce null columns for Delta Lake compatibility
        df = self._coerce_null_columns(df)

        table_name = _path_to_table_name(self._config.output_gold_path)
        records = df.to_dicts()
        await self._storage.write_gold_merged(
            table_name,
            records,
            run_id=run_id,
            sources_used=sources_used,
        )

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        # Convention: pipeline_name is "{provider}_{entity}"
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    def _normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
    ) -> pl.DataFrame:
        """Normalize join key columns for case-insensitive matching.

        Converts DOI, PMID, and other identifier columns to lowercase
        to ensure consistent joins across providers that may store
        identifiers in different cases.

        Args:
            df: DataFrame to normalize.
            join_keys: List of join key column names.

        Returns:
            DataFrame with normalized join key columns.

        Example:
            >>> df = pl.DataFrame({"doi": ["10.1038/NATURE12373"]})
            >>> normalized = merger._normalize_join_key_columns(df, ["doi"])
            >>> normalized["doi"][0]
            '10.1038/nature12373'
        """
        import polars as pl

        normalize_cols = [
            key
            for key in join_keys
            if key in self._NORMALIZE_JOIN_KEYS and key in df.columns
        ]

        if not normalize_cols:
            return df

        # Apply lowercase normalization to identifier columns
        return df.with_columns(
            [pl.col(col).str.to_lowercase().alias(col) for col in normalize_cols]
        )

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
    ) -> pl.DataFrame:
        """Apply join strategy (LEFT_OUTER/INNER/UNION) to combine DataFrames.

        Note: Join keys (doi, pmid, pmc_id) are normalized to lowercase before
        joining to ensure case-insensitive matching across providers.
        """
        merged = seed_df

        for enricher in enrichers:
            if enricher.pipeline not in enricher_dfs:
                continue

            enricher_df = enricher_dfs[enricher.pipeline]
            join_keys = list(enricher.join_keys)

            # Normalize join key columns for case-insensitive matching
            # This ensures DOIs like "10.1038/NATURE" match "10.1038/nature"
            merged = self._normalize_join_key_columns(merged, join_keys)
            enricher_df = self._normalize_join_key_columns(enricher_df, join_keys)

            # Find common columns to avoid duplicates
            seed_cols = set(merged.columns)
            enricher_cols = set(enricher_df.columns)
            common_cols = seed_cols & enricher_cols - set(join_keys)

            # Rename common columns in enricher with prefix
            prefix = f"{enricher.pipeline}_"
            enricher_df = enricher_df.rename(
                {col: f"{prefix}{col}" for col in common_cols}
            )

            # Apply join based on strategy
            how = self._get_polars_join_type()

            # Handle multiple join keys with fallback
            if len(join_keys) > 1:
                # Try primary key first
                primary_key = join_keys[0]
                if primary_key in merged.columns and primary_key in enricher_df.columns:
                    merged = merged.join(
                        enricher_df,
                        on=primary_key,
                        how=how,
                        suffix=f"_{enricher.pipeline}",
                    )
                    continue

            # Single key join
            primary_key = join_keys[0]
            if primary_key in merged.columns and primary_key in enricher_df.columns:
                merged = merged.join(
                    enricher_df,
                    on=primary_key,
                    how=how,
                    suffix=f"_{enricher.pipeline}",
                )

        return merged

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

    def _resolve_conflicts(
        self,
        df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
    ) -> pl.DataFrame:
        """Apply conflict resolution based on configured strategy."""

        match self._config.conflict_resolution:
            case ConflictResolution.SEED_PRIORITY:
                return self._coalesce_prefer_seed(df, enrichers)
            case ConflictResolution.ENRICHER_PRIORITY:
                return self._coalesce_prefer_enricher(df, enrichers)
            case ConflictResolution.COALESCE:
                return self._coalesce_first_non_null(df, enrichers)
            case ConflictResolution.EXPLICIT_RULES:
                return self._apply_explicit_rules(df, enrichers)
            case ConflictResolution.LATEST_TIMESTAMP:
                # Would require timestamp columns - fall back to seed
                return self._coalesce_prefer_seed(df, enrichers)
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
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Coalesce preferring seed values."""
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = f"{enricher.pipeline}_"
            for col in list(
                result.columns
            ):  # Copy list to avoid mutation during iteration
                if col.startswith(prefix):
                    base_col = col[len(prefix) :]
                    if base_col in result.columns:
                        # Check type compatibility before coalescing
                        if self._can_coalesce(result, base_col, col):
                            # Coalesce seed (base) over enricher
                            result = result.with_columns(
                                pl.coalesce(pl.col(base_col), pl.col(col)).alias(
                                    base_col
                                )
                            ).drop(col)
                        else:
                            # Incompatible types - keep seed value, drop enricher
                            self._logger.debug(
                                "Skipping coalesce for incompatible types",
                                seed_col=base_col,
                                enricher_col=col,
                                seed_type=str(result[base_col].dtype),
                                enricher_type=str(result[col].dtype),
                            )
                            result = result.drop(col)
        return result

    def _coalesce_prefer_enricher(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Coalesce preferring enricher values."""
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = f"{enricher.pipeline}_"
            for col in list(
                result.columns
            ):  # Copy list to avoid mutation during iteration
                if col.startswith(prefix):
                    base_col = col[len(prefix) :]
                    if base_col in result.columns:
                        # Check type compatibility before coalescing
                        if self._can_coalesce(result, base_col, col):
                            # Coalesce enricher over seed (base)
                            result = result.with_columns(
                                pl.coalesce(pl.col(col), pl.col(base_col)).alias(
                                    base_col
                                )
                            ).drop(col)
                        else:
                            # Incompatible types - prefer enricher if non-null exists
                            self._logger.debug(
                                "Skipping coalesce for incompatible types",
                                seed_col=base_col,
                                enricher_col=col,
                                seed_type=str(result[base_col].dtype),
                                enricher_type=str(result[col].dtype),
                            )
                            result = result.drop(col)
        return result

    def _coalesce_first_non_null(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Coalesce taking first non-null value."""
        # Same as seed priority for now
        return self._coalesce_prefer_seed(df, enrichers)

    def _apply_explicit_rules(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Apply explicit field priority rules."""
        import polars as pl

        result = df

        for field, priorities in self._config.field_priorities.items():
            # Find all columns for this field
            columns = [field]  # Seed column
            for enricher in enrichers:
                prefixed = f"{enricher.pipeline}_{field}"
                if prefixed in df.columns:
                    columns.append(prefixed)

            if len(columns) <= 1:
                continue

            # Reorder columns by priority
            ordered_cols = []
            for source in priorities:
                if source == "seed" or source == "chembl":  # Seed convention
                    if field in columns:
                        ordered_cols.append(field)
                else:
                    prefixed = f"{source}_{field}"
                    if prefixed in columns:
                        ordered_cols.append(prefixed)

            # Add any remaining columns not in priority list
            for col in columns:
                if col not in ordered_cols:
                    ordered_cols.append(col)

            if ordered_cols:
                # Filter to only compatible types for coalescing
                base_col = ordered_cols[0]
                compatible_cols = [base_col]
                cols_to_drop = []

                for col in ordered_cols[1:]:
                    if self._can_coalesce(result, base_col, col):
                        compatible_cols.append(col)
                    else:
                        # Incompatible type - mark for dropping
                        self._logger.debug(
                            "Skipping column with incompatible type in explicit rules",
                            field=field,
                            incompatible_col=col,
                            base_type=str(result[base_col].dtype),
                            col_type=str(result[col].dtype),
                        )
                        cols_to_drop.append(col)

                # Coalesce only compatible columns
                if len(compatible_cols) > 1:
                    result = result.with_columns(
                        pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(field)
                    )

                # Drop all non-base columns (both coalesced and incompatible)
                for col in ordered_cols[1:]:
                    if col != field and col in result.columns:
                        result = result.drop(col)

        return result

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
    ) -> pl.DataFrame:
        """Add lineage metadata columns to DataFrame."""
        import polars as pl

        # Build enrichment status dict
        status_dict = {
            name: result.status.value for name, result in enrichment_results.items()
        }

        # Add lineage columns
        return df.with_columns(
            [
                pl.lit(run_id).alias("_composite_run_id"),
                pl.lit(str(sources_used)).alias("_source_providers"),
                pl.lit(str(status_dict)).alias("_enrichment_status"),
                pl.lit(datetime.now(tz=UTC).isoformat()).alias("_lineage_created_at"),
            ]
        )

    def _count_enriched_records(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> int:
        """Count records with at least one enrichment."""
        # Check if any enricher-prefixed columns are non-null
        # This is approximate - relies on column naming convention
        enriched_count = 0
        for enricher in enrichers:
            prefix = f"{enricher.pipeline}_"
            enricher_cols = [c for c in df.columns if c.startswith(prefix)]
            if enricher_cols:
                # Check first enricher column for non-null
                col = enricher_cols[0]
                enriched_count = max(
                    enriched_count, len(df.filter(df[col].is_not_null()))
                )
        return enriched_count

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
