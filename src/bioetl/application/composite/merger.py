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
PrefixStrategy = Literal["provider", "entity", "both", "pipeline"]

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
                qualified_count=len([c for c in seed_df.columns if "." in c and not c.startswith("_")]),
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

        # Calculate statistics before writing
        records_merged = len(merged_df)
        records_enriched = self._count_enriched_records(
            merged_df, enrichers, effective_seed_pipeline
        )

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

    def _determine_prefix_strategy(
        self,
        seed_provider: str,
        seed_entity: str,
        enricher_provider: str,
        enricher_entity: str,
    ) -> PrefixStrategy:
        """Determine column prefix strategy based on provider/entity relationship.

        Determines how to prefix enricher columns to avoid conflicts
        while maintaining semantic clarity.

        Args:
            seed_provider: Provider name of the seed pipeline.
            seed_entity: Entity name of the seed pipeline.
            enricher_provider: Provider name of the enricher pipeline.
            enricher_entity: Entity name of the enricher pipeline.

        Returns:
            Strategy to use:
            - "provider": Cross-provider merge (same entity, different providers).
              Prefix with provider name. Example: "crossref.doi"
            - "entity": Cross-entity merge (same provider, different entities).
              Prefix with entity name. Example: "activity.chembl_id"
            - "both": Cross-provider-entity merge (different providers AND entities).
              Prefix with provider.entity. Example: "pubchem.compound.name"
            - "pipeline": Fallback when same provider and entity.
              Use full pipeline name. Example: "chembl_publication_extra.doi"

        Example:
            >>> merger._determine_prefix_strategy("chembl", "publication",
            ...                                    "crossref", "publication")
            'provider'
            >>> merger._determine_prefix_strategy("chembl", "publication",
            ...                                    "chembl", "activity")
            'entity'
            >>> merger._determine_prefix_strategy("chembl", "publication",
            ...                                    "pubchem", "compound")
            'both'
        """
        same_provider = seed_provider.lower() == enricher_provider.lower()
        same_entity = seed_entity.lower() == enricher_entity.lower()

        if same_entity and not same_provider:
            # Cross-provider merge: same entity, different providers
            return "provider"
        elif same_provider and not same_entity:
            # Cross-entity merge: same provider, different entities
            return "entity"
        elif not same_provider and not same_entity:
            # Cross-provider-entity merge: different providers AND entities
            return "both"
        else:
            # Same provider and entity - use full pipeline name
            return "pipeline"

    def _column_contains_identifier(
        self,
        column: str,
        identifier: str,
    ) -> bool:
        """Check if column name already contains the identifier (case-insensitive).

        Used to avoid redundant prefixes like "crossref.crossref_doi".

        Args:
            column: Column name to check.
            identifier: Identifier to search for (provider or entity name).

        Returns:
            True if column contains the identifier (case-insensitive).

        Example:
            >>> merger._column_contains_identifier("crossref_doi", "crossref")
            True
            >>> merger._column_contains_identifier("doi", "crossref")
            False
            >>> merger._column_contains_identifier("CROSSREF.DOI", "crossref")
            True
            >>> merger._column_contains_identifier("chembl_id", "chembl")
            True
        """
        return identifier.lower() in column.lower()

    def _build_prefix(
        self,
        strategy: PrefixStrategy,
        provider: str,
        entity: str,
        pipeline: str,
    ) -> str:
        """Build column prefix based on strategy.

        Args:
            strategy: Prefix strategy to use.
            provider: Provider name.
            entity: Entity name.
            pipeline: Full pipeline name (fallback).

        Returns:
            Prefix string WITHOUT trailing dot.

        Example:
            >>> merger._build_prefix("provider", "crossref", "publication",
            ...                       "crossref_publication")
            'crossref'
            >>> merger._build_prefix("entity", "chembl", "activity",
            ...                       "chembl_activity")
            'activity'
            >>> merger._build_prefix("both", "pubchem", "compound",
            ...                       "pubchem_compound")
            'pubchem.compound'
        """
        match strategy:
            case "provider":
                return provider
            case "entity":
                return entity
            case "both":
                return f"{provider}.{entity}"
            case "pipeline":
                return pipeline

    def _apply_column_prefix(
        self,
        df: pl.DataFrame,
        columns: set[str],
        prefix: str,
        exclude_columns: set[str],
    ) -> pl.DataFrame:
        """Apply prefix to specified columns.

        Renames columns by adding a prefix with dot separator.
        Excludes join keys and columns already containing the identifier.

        Args:
            df: DataFrame to modify.
            columns: Set of column names to potentially rename.
            prefix: Prefix to add (WITHOUT trailing dot).
            exclude_columns: Columns to exclude from renaming (join keys, etc.).

        Returns:
            DataFrame with renamed columns.

        Example:
            >>> df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
            >>> result = merger._apply_column_prefix(
            ...     df, {"title"}, "crossref", {"doi"}
            ... )
            >>> result.columns
            ['doi', 'crossref.title']
        """
        rename_map = {}
        for col in columns:
            if col not in exclude_columns:
                rename_map[col] = f"{prefix}.{col}"

        if rename_map:
            self._logger.debug(
                "Applying column prefix",
                prefix=prefix,
                columns=list(rename_map.keys()),
            )
            return df.rename(rename_map)
        return df

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
        """Apply join strategy with intelligent column renaming.

        Column renaming strategy (by merge type):
        - Cross-provider (same entity): prefix with provider name (e.g., "crossref.doi")
        - Cross-entity (same provider): prefix with entity name (e.g., "activity.name")
        - Cross-provider-entity: prefix with provider.entity (e.g., "pubchem.compound.name")

        Join keys (doi, pmid, pmc_id) are normalized to lowercase for
        case-insensitive matching across providers.

        Conflict resolution:
        - After prefixing, remaining conflicts get .A/.B suffixes

        Args:
            seed_df: Seed DataFrame to join to.
            enricher_dfs: Mapping of enricher pipeline name to DataFrame.
            enrichers: Sequence of enricher configurations.
            seed_pipeline: Seed pipeline name (e.g., "chembl_publication").
                If None, falls back to legacy underscore prefix naming.

        Returns:
            Merged DataFrame with all enricher data joined.

        Example:
            >>> # Cross-provider merge: chembl_publication + crossref_publication
            >>> # Column "title" in enricher → "crossref.title"
            >>> merged = await merger._apply_joins(
            ...     seed_df, enricher_dfs, enrichers, "chembl_publication"
            ... )
        """
        merged = seed_df

        # Parse seed pipeline for intelligent prefix strategy
        seed_provider: str | None = None
        seed_entity: str | None = None
        if seed_pipeline:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
            except ValueError:
                self._logger.warning(
                    "Could not parse seed pipeline name, using legacy prefix",
                    seed_pipeline=seed_pipeline,
                )

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

            # Find columns to prefix: all columns EXCEPT the primary join key
            # Secondary join keys (title, doi when not primary) SHOULD be prefixed
            # to avoid Polars adding its own suffix during join
            non_join_cols = set(enricher_df.columns) - primary_key_set

            # Determine prefix strategy
            if seed_provider is not None and seed_entity is not None:
                try:
                    enricher_provider, enricher_entity = self._parse_pipeline_name(
                        enricher.pipeline
                    )

                    strategy = self._determine_prefix_strategy(
                        seed_provider,
                        seed_entity,
                        enricher_provider,
                        enricher_entity,
                    )

                    prefix = self._build_prefix(
                        strategy,
                        enricher_provider,
                        enricher_entity,
                        enricher.pipeline,
                    )

                    self._logger.debug(
                        "Column rename strategy determined",
                        enricher=enricher.pipeline,
                        strategy=strategy,
                        prefix=prefix,
                    )

                    # Find columns that already contain the identifier
                    already_prefixed = {
                        col
                        for col in non_join_cols
                        if self._column_contains_identifier(col, enricher_provider)
                        or self._column_contains_identifier(col, enricher_entity)
                    }

                    # Apply prefix to non-join columns
                    # Only exclude primary key, secondary keys get prefixed
                    enricher_df = self._apply_column_prefix(
                        enricher_df,
                        non_join_cols - already_prefixed,
                        prefix,
                        primary_key_set,
                    )

                except ValueError:
                    # Fallback to legacy prefix if parsing fails
                    self._logger.warning(
                        "Could not parse enricher pipeline, using legacy prefix",
                        enricher=enricher.pipeline,
                    )
                    enricher_df = self._apply_legacy_prefix(
                        enricher_df, enricher.pipeline, non_join_cols, primary_key_set
                    )
            else:
                # No seed pipeline provided - use legacy prefix
                enricher_df = self._apply_legacy_prefix(
                    enricher_df, enricher.pipeline, non_join_cols, primary_key_set
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

    def _apply_legacy_prefix(
        self,
        df: pl.DataFrame,
        pipeline: str,
        columns: set[str],
        join_keys: set[str],
    ) -> pl.DataFrame:
        """Apply legacy underscore prefix to columns (backwards compatibility).

        Args:
            df: DataFrame to modify.
            pipeline: Pipeline name to use as prefix.
            columns: Columns to potentially rename.
            join_keys: Columns to exclude (join keys).

        Returns:
            DataFrame with legacy-prefixed columns.
        """
        # Find common columns between seed and enricher
        common_cols = columns - join_keys
        rename_map = {col: f"{pipeline}_{col}" for col in common_cols}

        if rename_map:
            self._logger.debug(
                "Applying legacy underscore prefix",
                pipeline=pipeline,
                columns=list(rename_map.keys()),
            )
            return df.rename(rename_map)
        return df

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
        seed_pipeline: str | None,
    ) -> str:
        """Get the column prefix used for an enricher.

        Computes the prefix that was (or would be) applied to enricher columns
        during `_apply_joins`. Used for conflict resolution.

        Args:
            enricher_pipeline: Enricher pipeline name.
            seed_pipeline: Seed pipeline name (may be None for legacy mode).

        Returns:
            Prefix string WITH trailing dot or underscore.

        Example:
            >>> merger._get_enricher_prefix("crossref_publication", "chembl_publication")
            'crossref.'  # Cross-provider (same entity)
            >>> merger._get_enricher_prefix("chembl_activity", "chembl_publication")
            'activity.'  # Cross-entity (same provider)
            >>> merger._get_enricher_prefix("crossref_publication", None)
            'crossref_publication_'  # Legacy mode
        """
        if not seed_pipeline:
            # Legacy mode: use full pipeline name with underscore
            return f"{enricher_pipeline}_"

        try:
            seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
            enricher_provider, enricher_entity = self._parse_pipeline_name(
                enricher_pipeline
            )

            strategy = self._determine_prefix_strategy(
                seed_provider, seed_entity, enricher_provider, enricher_entity
            )

            prefix = self._build_prefix(
                strategy, enricher_provider, enricher_entity, enricher_pipeline
            )
            return f"{prefix}."

        except ValueError:
            # Fallback to legacy if parsing fails
            return f"{enricher_pipeline}_"

    def _extract_base_column(self, column: str, prefix: str) -> str | None:
        """Extract base column name from a prefixed column.

        Args:
            column: Column name that may have a prefix.
            prefix: Prefix to strip (WITH trailing dot or underscore).

        Returns:
            Base column name if column starts with prefix, None otherwise.

        Example:
            >>> merger._extract_base_column("crossref.title", "crossref.")
            'title'
            >>> merger._extract_base_column("activity.name", "activity.")
            'name'
            >>> merger._extract_base_column("title", "crossref.")
            None
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

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with enricher columns coalesced into base columns.
        """
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
            for col in list(
                result.columns
            ):  # Copy list to avoid mutation during iteration
                base_col = self._extract_base_column(col, prefix)
                if base_col is not None and base_col in result.columns:
                    # Check type compatibility before coalescing
                    if self._can_coalesce(result, base_col, col):
                        # Coalesce seed (base) over enricher
                        result = result.with_columns(
                            pl.coalesce(pl.col(base_col), pl.col(col)).alias(base_col)
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
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Coalesce preferring enricher values.

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            DataFrame with enricher columns coalesced into base columns.
        """
        import polars as pl

        result = df
        for enricher in enrichers:
            prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
            for col in list(
                result.columns
            ):  # Copy list to avoid mutation during iteration
                base_col = self._extract_base_column(col, prefix)
                if base_col is not None and base_col in result.columns:
                    # Check type compatibility before coalescing
                    if self._can_coalesce(result, base_col, col):
                        # Coalesce enricher over seed (base)
                        result = result.with_columns(
                            pl.coalesce(pl.col(col), pl.col(base_col)).alias(base_col)
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
        """Collect all columns for a field including enricher prefixed versions.

        Supports both new dot-based prefixes (crossref.title) and legacy
        underscore prefixes (crossref_publication_title).

        Args:
            field: Base field name.
            enrichers: Sequence of enricher configurations.
            available_columns: Set of available column names in DataFrame.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            List of column names including seed and enricher versions.
        """
        columns = [field] if field in available_columns else []
        for enricher in enrichers:
            # Get the prefix that was used for this enricher
            prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
            # Prefix includes trailing dot/underscore, so: "crossref." + "title"
            prefixed = f"{prefix}{field}"
            if prefixed in available_columns:
                columns.append(prefixed)
        return columns

    def _order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: Sequence[str],
        seed_pipeline: str | None = None,
    ) -> list[str]:
        """Order columns by priority list, appending any remaining columns.

        Args:
            field: Base field name.
            columns: List of available columns for this field.
            priorities: Ordered list of source priorities (provider names or "seed").
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            Ordered list of columns by priority.
        """
        ordered_cols: list[str] = []

        for source in priorities:
            if source in ("seed", "chembl"):  # Seed convention
                if field in columns and field not in ordered_cols:
                    ordered_cols.append(field)
            else:
                # Try new dot-based prefix: "crossref.title"
                dot_prefixed = f"{source}.{field}"
                if dot_prefixed in columns and dot_prefixed not in ordered_cols:
                    ordered_cols.append(dot_prefixed)
                    continue

                # Try legacy underscore prefix: "crossref_publication_title"
                # The source might be just "crossref" but column is "crossref_publication_title"
                for col in columns:
                    if col.startswith(f"{source}_") and col.endswith(f"_{field}"):
                        if col not in ordered_cols:
                            ordered_cols.append(col)
                        break

        # Add remaining columns not in priority list
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

            # Coalesce compatible columns
            if len(compatible_cols) > 1:
                result = result.with_columns(
                    pl.coalesce(*[pl.col(c) for c in compatible_cols]).alias(field)
                )

            # Drop all non-base columns
            cols_to_drop = [
                col
                for col in ordered_cols[1:]
                if col != field and col in result.columns
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

        Args:
            df: Merged DataFrame with prefixed columns.
            enrichers: Enricher configurations.
            seed_pipeline: Seed pipeline name for prefix computation.

        Returns:
            Count of records with at least one non-null enricher column.
        """
        # Check if any enricher-prefixed columns are non-null
        # This is approximate - relies on column naming convention
        enriched_count = 0
        for enricher in enrichers:
            prefix = self._get_enricher_prefix(enricher.pipeline, seed_pipeline)
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
