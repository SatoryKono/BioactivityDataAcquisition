"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.deduplication import EnricherDeduplicator
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
        self._deduplicator = EnricherDeduplicator(logger)
        self._renamer = ColumnRenamer(logger)
        self._orderer = ColumnOrderer(logger)

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
    ) -> MergeResult:
        """Merge seed and enricher data into unified output.

        Args:
            seed_table: Path to seed Silver table (e.g., "silver/chembl/publication").
            enrichers: Sequence of enricher configurations.
            enrichment_results: Results from enricher execution.
            run_id: Composite pipeline run ID.
            seed_pipeline: Seed pipeline name (e.g., "chembl_publication").
                If None, will be inferred from seed_table path.
                Used for intelligent column renaming during merge.

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
        if effective_seed_pipeline:
            self._logger.debug(
                "Using seed pipeline for column renaming",
                seed_pipeline=effective_seed_pipeline,
            )
            seed_df = self._renamer.rename_dataframe(
                seed_df,
                effective_seed_pipeline,
                exclude_join_keys=True,
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

        # Step 3: Apply joins with intelligent column renaming
        merged_df = await self._apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline=effective_seed_pipeline,
        )

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
        )

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

    def _infer_pipeline_from_table(self, table_path: str) -> str | None:
        """Infer pipeline name from Silver table path.

        Converts a table path like "silver/chembl/publication" to
        pipeline name "chembl_publication".

        Args:
            table_path: Silver table path.

        Returns:
            Pipeline name or None if cannot be inferred.

        Example:
            >>> merger._infer_pipeline_from_table("silver/chembl/publication")
            'chembl_publication'
            >>> merger._infer_pipeline_from_table("silver/crossref/publication")
            'crossref_publication'
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

    def _parse_pipeline_name(self, pipeline: str) -> tuple[str, str]:
        """Parse pipeline name into (provider, entity).

        Pipeline names follow the format "{provider}_{entity}".
        For example: 'chembl_publication' → ('chembl', 'publication').

        Args:
            pipeline: Pipeline name in format "provider_entity".

        Returns:
            Tuple of (provider, entity).

        Raises:
            ValueError: If pipeline name doesn't contain underscore separator.

        Example:
            >>> merger._parse_pipeline_name("chembl_publication")
            ('chembl', 'publication')
            >>> merger._parse_pipeline_name("crossref_publication")
            ('crossref', 'publication')
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return (parts[0], parts[1])

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name.

        Args:
            column: Column name, possibly in qualified format.

        Returns:
            Field name if qualified (x.y.z → z), or original column name if not.

        Example:
            >>> merger._extract_field_from_qualified("chembl.publication.title")
            'title'
            >>> merger._extract_field_from_qualified("title")
            'title'
            >>> merger._extract_field_from_qualified("crossref.title")
            'crossref.title'
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]
        return column

    def _find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Find next available suffix for a conflicting column.

        Iterates through A, B, C, ... Z, AA, AB, ... to find an unused suffix.

        Args:
            base_col: Base column name without suffix.
            existing_cols: Set of existing column names.

        Returns:
            Next available suffix letter(s).

        Example:
            >>> merger._find_next_suffix("title", {"title", "title.A", "title.B"})
            'C'
            >>> merger._find_next_suffix("title", {"title"})
            'A'
        """
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

        After prefix application, there may still be conflicts when:
        - Seed already has a prefixed column (e.g., "crossref.title")
        - Enricher gets the same prefix (e.g., "crossref.title")

        Resolution: Keep seed columns unchanged, add incremental suffixes
        (A, B, C, ...) to enricher columns.

        Args:
            seed_df: Seed DataFrame (columns are NOT renamed).
            enricher_df: Enricher DataFrame (already with prefixes applied).
            join_keys: Set of join key columns to exclude from conflict resolution.

        Returns:
            Tuple of (seed_df unchanged, modified_enricher_df) with conflicts resolved.

        Example:
            >>> seed = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
            >>> enricher = pl.DataFrame({"doi": ["10.1/a"], "title": ["T2"]})
            >>> seed_out, enricher_out = merger._detect_and_resolve_conflicts(
            ...     seed, enricher, {"doi"}
            ... )
            >>> seed_out.columns
            ['doi', 'title']
            >>> enricher_out.columns
            ['doi', 'title.A']
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

        Column renaming uses ColumnRenamer to apply {provider}.{entity}.{field}
        format to enricher columns for qualified column matching.

        Join keys (doi, pmid, pmc_id) are normalized to lowercase for
        case-insensitive matching across providers.

        Conflict resolution:
        - After prefixing, remaining conflicts get .A/.B suffixes

        Args:
            seed_df: Seed DataFrame to join to.
            enricher_dfs: Mapping of enricher pipeline name to DataFrame.
            enrichers: Sequence of enricher configurations.
            seed_pipeline: Seed pipeline name (unused, kept for compatibility).

        Returns:
            Merged DataFrame with all enricher data joined.

        Example:
            >>> # Cross-provider merge: chembl_publication + crossref_publication
            >>> # Column "title" in enricher → "crossref.publication.title"
            >>> merged = await merger._apply_joins(
            ...     seed_df, enricher_dfs, enrichers, "chembl_publication"
            ... )
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
            primary_key_set = {primary_key}

            # Deduplicate enricher before join to prevent fan-out
            enricher_df = self._deduplicator.deduplicate(
                enricher_df=enricher_df,
                join_keys=join_keys_list,
                enricher_name=enricher.pipeline,
            )

            # Normalize join key columns for case-insensitive matching
            # This ensures DOIs like "10.1038/NATURE" match "10.1038/nature"
            merged = self._normalize_join_key_columns(merged, join_keys_list)
            enricher_df = self._normalize_join_key_columns(enricher_df, join_keys_list)

            # Rename enricher columns to qualified format: {provider}.{entity}.{field}
            # Uses ColumnRenamer which excludes join keys automatically
            enricher_df = self._renamer.rename_dataframe(
                enricher_df,
                enricher.pipeline,
                exclude_join_keys=True,
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

            # Detect and resolve remaining conflicts
            # Only exclude primary key - secondary keys should be checked for conflicts
            merged, enricher_df = self._detect_and_resolve_conflicts(
                merged, enricher_df, primary_key_set
            )

            # Apply join based on strategy
            how = self._get_polars_join_type()

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
            if len(columns) <= 1:
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
                if enricher_qualified in available_columns and enricher_qualified not in columns:
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
                target_col = compatible_cols[0]  # Keep the first column name (qualified)
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(target_col)
                )

            # Drop all non-target columns
            cols_to_drop = [
                col
                for col in compatible_cols[1:]
                if col in result.columns
            ]
            if cols_to_drop:
                result = result.drop(cols_to_drop)

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
        any_enriched = pl.any_horizontal([pl.col(c).is_not_null() for c in enricher_cols])
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
