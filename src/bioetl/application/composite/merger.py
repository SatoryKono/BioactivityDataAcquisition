"""Merge Service.

Application Service that merges enriched data from multiple sources.
Implements join strategies and conflict resolution with lineage tracking.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Sequence

from bioetl.domain.composite.lineage import LineageBuilder, LineageMetadata
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus, MergeResult
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig, MergeConfig
    from bioetl.domain.ports import LoggerPort, StoragePort


class MergeService:
    """Merges enriched data from multiple sources.

    Implements join strategies and conflict resolution.
    Preserves lineage metadata for traceability.

    This service is responsible for:
    - Reading seed and enricher Silver tables
    - Applying join strategy (LEFT OUTER, INNER, UNION)
    - Resolving field conflicts between sources
    - Adding lineage metadata to each record
    - Writing merged data to Silver and Gold

    Attributes:
        merge_config: Merge configuration with strategy and paths.
        storage: Storage port for reading/writing tables.
        logger: Structured logger.

    Example:
        >>> merger = MergeService(
        ...     merge_config=merge_config,
        ...     storage=storage,
        ...     logger=logger,
        ... )
        >>> result = await merger.merge(
        ...     seed_table="silver/chembl/publication",
        ...     enrichers=enricher_configs,
        ...     enrichment_results=results,
        ...     run_id="abc-123",
        ... )
    """

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
    ) -> None:
        """Initialize merge service.

        Args:
            merge_config: Merge configuration.
            storage: Storage port for I/O.
            logger: Structured logger.
        """
        self._config = merge_config
        self._storage = storage
        self._logger = logger

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
    ) -> MergeResult:
        """Merge seed and enricher data into unified output.

        Execution flow:
        1. Read seed Silver table
        2. For each successful enricher, read and join
        3. Apply conflict resolution
        4. Add lineage metadata
        5. Write to Silver and Gold

        Args:
            seed_table: Path to seed Silver table.
            enrichers: Enricher configurations.
            enrichment_results: Results from enrichment phase.
            run_id: Composite run ID for lineage.

        Returns:
            MergeResult with statistics and paths.

        Example:
            >>> result = await merger.merge(
            ...     seed_table="silver/chembl/publication",
            ...     enrichers=enricher_configs,
            ...     enrichment_results={"crossref": success_result},
            ...     run_id="abc-123",
            ... )
            >>> result.records_merged
            100
        """
        started_at = datetime.now()

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

        # Step 6: Write to Silver
        self._logger.info(
            "Writing merged Silver table",
            path=self._config.output_silver_path,
            records=records_merged,
        )
        await self._storage.write_silver(
            df=merged_df,
            path=self._config.output_silver_path,
            mode="overwrite",
        )

        # Step 7: Write to Gold (with filtering if needed)
        self._logger.info(
            "Writing merged Gold table",
            path=self._config.output_gold_path,
            records=records_merged,
        )
        await self._storage.write_gold(
            df=merged_df,
            path=self._config.output_gold_path,
            mode="overwrite",
        )

        completed_at = datetime.now()
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
        """Read a Silver table using storage port."""
        return await self._storage.read_silver(path)

    def _infer_silver_table(self, pipeline_name: str) -> str:
        """Infer Silver table path from pipeline name."""
        # Convention: pipeline_name is "{provider}_{entity}"
        parts = pipeline_name.split("_", 1)
        if len(parts) == 2:
            provider, entity = parts
            return f"silver/{provider}/{entity}"
        return f"silver/{pipeline_name}"

    async def _apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
    ) -> pl.DataFrame:
        """Apply join strategy to combine DataFrames.

        Uses the configured merge strategy:
        - LEFT_OUTER: All seed records, enrichments nullable
        - INNER: Only matched records
        - UNION: All records from any source

        Args:
            seed_df: Seed DataFrame.
            enricher_dfs: Mapping of enricher name to DataFrame.
            enrichers: Enricher configurations with join keys.

        Returns:
            Merged DataFrame.
        """
        import polars as pl

        merged = seed_df

        for enricher in enrichers:
            if enricher.pipeline not in enricher_dfs:
                continue

            enricher_df = enricher_dfs[enricher.pipeline]
            join_keys = list(enricher.join_keys)

            # Find common columns to avoid duplicates
            seed_cols = set(merged.columns)
            enricher_cols = set(enricher_df.columns)
            common_cols = seed_cols & enricher_cols - set(join_keys)

            # Rename common columns in enricher with prefix
            prefix = f"{enricher.pipeline}_"
            enricher_df = enricher_df.rename({
                col: f"{prefix}{col}" for col in common_cols
            })

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

    def _get_polars_join_type(self) -> str:
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
        """Apply conflict resolution strategy.

        When multiple sources provide the same field, resolve conflicts
        according to the configured strategy.

        Args:
            df: Merged DataFrame with potential conflicts.
            enricher_dfs: Source DataFrames for reference.
            enrichers: Enricher configurations.

        Returns:
            DataFrame with conflicts resolved.
        """
        import polars as pl

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

    def _coalesce_prefer_seed(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Coalesce preferring seed values."""
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = f"{enricher.pipeline}_"
            for col in df.columns:
                if col.startswith(prefix):
                    base_col = col[len(prefix):]
                    if base_col in df.columns:
                        # Coalesce seed (base) over enricher
                        result = result.with_columns(
                            pl.coalesce(pl.col(base_col), pl.col(col)).alias(base_col)
                        ).drop(col)
        return result

    def _coalesce_prefer_enricher(
        self, df: pl.DataFrame, enrichers: Sequence[EnricherConfig]
    ) -> pl.DataFrame:
        """Coalesce preferring enricher values."""
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = f"{enricher.pipeline}_"
            for col in df.columns:
                if col.startswith(prefix):
                    base_col = col[len(prefix):]
                    if base_col in df.columns:
                        # Coalesce enricher over seed (base)
                        result = result.with_columns(
                            pl.coalesce(pl.col(col), pl.col(base_col)).alias(base_col)
                        ).drop(col)
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
                # Coalesce in priority order
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in ordered_cols]).alias(field)
                )
                # Drop prefixed columns
                for col in ordered_cols[1:]:
                    if col != field:
                        result = result.drop(col)

        return result

    def _add_lineage(
        self,
        df: pl.DataFrame,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        sources_used: list[str],
    ) -> pl.DataFrame:
        """Add lineage metadata to each record.

        Adds columns tracking composite run, sources, and enrichment status.

        Args:
            df: Merged DataFrame.
            enrichment_results: Enrichment results for status.
            run_id: Composite run ID.
            sources_used: List of sources that contributed.

        Returns:
            DataFrame with lineage columns.
        """
        import polars as pl

        # Build enrichment status dict
        status_dict = {
            name: result.status.value
            for name, result in enrichment_results.items()
        }

        # Add lineage columns
        return df.with_columns([
            pl.lit(run_id).alias("_composite_run_id"),
            pl.lit(str(sources_used)).alias("_source_providers"),
            pl.lit(str(status_dict)).alias("_enrichment_status"),
            pl.lit(datetime.now().isoformat()).alias("_lineage_created_at"),
        ])

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
                    enriched_count,
                    len(df.filter(df[col].is_not_null()))
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
