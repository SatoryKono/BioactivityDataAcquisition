"""Enrichment cross-validator for composite pipelines.

Compares paired fields between seed and each enricher after join but
before conflict resolution. Detects mismatches and applies verdicts:
- PASS: 0 mismatches
- WARNING: 1 mismatch (configurable)
- ENRICHER_ERROR: 2+ mismatches -> null all enricher columns
- QUARANTINE: 2+ enrichers with ENRICHER_ERROR -> flag seed record

See plan: Pre-Merge Cross-Validation for Composite Publication Pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    CrossValidationStats,
    CrossValidationVerdict,
    EnricherCVStats,
)
from bioetl.domain.services.text_similarity import jaccard_similarity

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import (
        CrossValidationConfig,
        EnricherFieldPairing,
    )
    from bioetl.domain.ports import LoggerPort


class EnrichmentCrossValidator:
    """Validates enricher data consistency against seed before merge.

    For each enricher with configured field pairings, compares shared fields
    between seed and enricher columns in the merged DataFrame. Mismatches
    are counted per record to determine verdicts.

    Usage:
        validator = EnrichmentCrossValidator(config, logger)
        df, stats = validator.validate(merged_df, enricher_pipelines, seed_pipeline)
    """

    def __init__(
        self,
        config: CrossValidationConfig,
        logger: LoggerPort,
    ) -> None:
        self._config = config
        self._logger = logger

    def validate(
        self,
        merged_df: pl.DataFrame,
        enricher_pipelines: list[str],
        seed_pipeline: str,
    ) -> tuple[pl.DataFrame, CrossValidationStats]:
        """Run cross-validation on merged DataFrame.

        Args:
            merged_df: DataFrame after joins (seed + enricher columns present).
            enricher_pipelines: List of enricher pipeline names that were joined.
            seed_pipeline: Seed pipeline name (e.g., "chembl_publication").

        Returns:
            Tuple of (modified DataFrame, CrossValidationStats).
            DataFrame has enricher columns nullified where ENRICHER_ERROR,
            and _cv_quarantine column added where applicable.
        """
        import polars as pl

        if not self._config.enabled:
            return merged_df, CrossValidationStats(total_records=len(merged_df))

        seed_provider, seed_entity = self._parse_pipeline(seed_pipeline)
        total_records = len(merged_df)
        enricher_stats_list: list[EnricherCVStats] = []

        # Track enricher error counts per row (for quarantine decision)
        enricher_error_counts = pl.Series(
            "_cv_enricher_errors", [0] * total_records, dtype=pl.Int32
        )

        # Track any warnings per row
        has_warning = pl.Series(
            "_cv_has_warning", [False] * total_records, dtype=pl.Boolean
        )

        for enricher_pipeline in enricher_pipelines:
            pairing = self._config.get_pairing(enricher_pipeline)
            if pairing is None:
                continue

            enricher_provider, enricher_entity = self._parse_pipeline(enricher_pipeline)

            # Count mismatches per row for this enricher
            mismatch_count, compared_count = self._count_mismatches_vectorized(
                merged_df,
                pairing,
                seed_provider,
                seed_entity,
                enricher_provider,
                enricher_entity,
            )

            # Determine verdicts
            is_error = mismatch_count >= self._config.error_threshold
            is_warning = (mismatch_count >= self._config.warning_threshold) & ~is_error
            is_pass = ~is_error & ~is_warning

            error_count = is_error.sum()
            warn_count = is_warning.sum()
            pass_count = is_pass.sum()

            self._logger.info(
                "Cross-validation for enricher",
                enricher=enricher_pipeline,
                passed=int(pass_count),
                warned=int(warn_count),
                errored=int(error_count),
            )

            enricher_stats_list.append(
                EnricherCVStats(
                    enricher=enricher_pipeline,
                    total_records=total_records,
                    passed=int(pass_count),
                    warned=int(warn_count),
                    errored=int(error_count),
                )
            )

            # Null enricher columns where ENRICHER_ERROR
            if int(error_count) > 0:
                enricher_prefix = f"{enricher_provider}.{enricher_entity}."
                enricher_cols = [
                    c for c in merged_df.columns if c.startswith(enricher_prefix)
                ]
                if enricher_cols:
                    merged_df = merged_df.with_columns(
                        [
                            pl.when(is_error)
                            .then(pl.lit(None))
                            .otherwise(pl.col(c))
                            .alias(c)
                            for c in enricher_cols
                        ]
                    )
                    self._logger.info(
                        "Nullified enricher columns for error records",
                        enricher=enricher_pipeline,
                        columns_nullified=len(enricher_cols),
                        records_affected=int(error_count),
                    )

            # Accumulate per-row error counts and warnings
            enricher_error_counts = enricher_error_counts + is_error.cast(pl.Int32)
            has_warning = has_warning | is_warning

        # Determine quarantine (2+ enricher errors)
        is_quarantine = enricher_error_counts >= self._config.quarantine_threshold
        quarantine_count = int(is_quarantine.sum())

        # Add CV metadata columns
        merged_df = merged_df.with_columns(
            [
                has_warning.alias("_cv_warn"),
                (enricher_error_counts > 0).alias("_cv_error"),
                is_quarantine.alias("_cv_quarantine"),
            ]
        )

        # Build quarantine payloads
        quarantine_payloads: list[dict[str, object]] = []
        if quarantine_count > 0:
            quarantine_df = merged_df.filter(is_quarantine)
            # Extract seed columns only (for quarantine record)
            seed_prefix = f"{seed_provider}.{seed_entity}."
            seed_cols = [c for c in quarantine_df.columns if c.startswith(seed_prefix)]
            if seed_cols:
                quarantine_payloads = quarantine_df.select(seed_cols).to_dicts()

            self._logger.warning(
                "Seed records quarantined due to multiple enricher errors",
                quarantine_count=quarantine_count,
                threshold=self._config.quarantine_threshold,
            )

        # Compute aggregate stats
        errored_count = int((enricher_error_counts > 0).sum())
        warned_count = int((has_warning & (enricher_error_counts == 0)).sum())
        passed_count = total_records - errored_count - warned_count

        stats = CrossValidationStats(
            total_records=total_records,
            passed=passed_count,
            warned=warned_count,
            errored=errored_count,
            quarantined=quarantine_count,
            enricher_stats=tuple(enricher_stats_list),
        )

        self._logger.info(
            "Cross-validation completed",
            total=total_records,
            passed=passed_count,
            warned=warned_count,
            errored=errored_count,
            quarantined=quarantine_count,
        )

        return merged_df, stats

    def _count_mismatches_vectorized(
        self,
        df: pl.DataFrame,
        pairing: EnricherFieldPairing,
        seed_provider: str,
        seed_entity: str,
        enricher_provider: str,
        enricher_entity: str,
    ) -> tuple[pl.Series, pl.Series]:
        """Count field mismatches per row using vectorized Polars operations.

        For each field in the pairing:
        1. Resolve qualified column names
        2. Skip if either column doesn't exist
        3. Compare values where both are non-null
        4. Count mismatches

        Args:
            df: Merged DataFrame.
            pairing: Field comparison specs for this enricher.
            seed_provider: Seed provider name.
            seed_entity: Seed entity name.
            enricher_provider: Enricher provider name.
            enricher_entity: Enricher entity name.

        Returns:
            Tuple of (mismatch_count Series, compared_count Series).
        """
        import polars as pl

        n = len(df)
        mismatch_total = pl.Series("_mm", [0] * n, dtype=pl.Int32)
        compared_total = pl.Series("_cmp", [0] * n, dtype=pl.Int32)

        for spec in pairing.fields:
            if spec.method == ComparisonMethod.SKIP:
                continue

            seed_col = f"{seed_provider}.{seed_entity}.{spec.field_name}"
            enricher_col = f"{enricher_provider}.{enricher_entity}.{spec.field_name}"

            if seed_col not in df.columns or enricher_col not in df.columns:
                self._logger.debug(
                    "Skipping CV field - column not found",
                    field=spec.field_name,
                    seed_col=seed_col,
                    enricher_col=enricher_col,
                )
                continue

            # Both non-null mask
            both_present = df[seed_col].is_not_null() & df[enricher_col].is_not_null()

            # For string columns, also check for empty strings
            seed_dtype = df[seed_col].dtype
            enricher_dtype = df[enricher_col].dtype
            if seed_dtype == pl.String or seed_dtype == pl.Utf8:
                both_present = both_present & (df[seed_col].str.len_chars() > 0)
            if enricher_dtype == pl.String or enricher_dtype == pl.Utf8:
                both_present = both_present & (df[enricher_col].str.len_chars() > 0)

            compared_total = compared_total + both_present.cast(pl.Int32)

            # Compute match for this field
            match_result = self._compare_field(
                df, seed_col, enricher_col, spec.method, spec.threshold
            )

            # Mismatch = both present AND not matching
            is_mismatch = both_present & ~match_result
            mismatch_total = mismatch_total + is_mismatch.cast(pl.Int32)

        return mismatch_total, compared_total

    def _compare_field(
        self,
        df: pl.DataFrame,
        seed_col: str,
        enricher_col: str,
        method: ComparisonMethod,
        threshold: float,
    ) -> pl.Series:
        """Compare a single field between seed and enricher.

        Returns a boolean Series where True = match, False = mismatch.
        Null values are treated as True (skip).

        Args:
            df: DataFrame containing both columns.
            seed_col: Qualified seed column name.
            enricher_col: Qualified enricher column name.
            method: Comparison method.
            threshold: Threshold for fuzzy/numeric.

        Returns:
            Boolean Series (True = match or skip, False = mismatch).
        """
        import polars as pl

        if method == ComparisonMethod.EXACT:
            return self._compare_exact(df, seed_col, enricher_col)
        elif method == ComparisonMethod.FUZZY:
            return self._compare_fuzzy(df, seed_col, enricher_col, threshold)
        elif method == ComparisonMethod.NUMERIC_TOLERANCE:
            return self._compare_numeric(df, seed_col, enricher_col, threshold)
        else:
            # SKIP or unknown -> treat as match
            return pl.Series([True] * len(df))

    def _compare_exact(
        self, df: pl.DataFrame, seed_col: str, enricher_col: str
    ) -> pl.Series:
        """Exact comparison after stripping whitespace.

        Casts both to String for consistent comparison.
        """
        import polars as pl

        s = df[seed_col].cast(pl.String).str.strip_chars()
        e = df[enricher_col].cast(pl.String).str.strip_chars()
        # Null-safe: if either is null, treat as "match" (skip)
        return s.eq(e) | s.is_null() | e.is_null()

    def _compare_fuzzy(
        self,
        df: pl.DataFrame,
        seed_col: str,
        enricher_col: str,
        threshold: float,
    ) -> pl.Series:
        """Fuzzy comparison using Jaccard similarity on word sets.

        Uses map_elements for row-by-row Jaccard computation.
        """
        import polars as pl

        def _fuzzy_match(row: dict) -> bool:  # type: ignore[type-arg]
            s_val = row["seed"]
            e_val = row["enricher"]
            if s_val is None or e_val is None:
                return True  # Skip nulls
            sim = jaccard_similarity(str(s_val), str(e_val))
            return sim >= threshold

        result = (
            df.select(
                pl.col(seed_col).alias("seed"),
                pl.col(enricher_col).alias("enricher"),
            )
            .select(
                pl.struct(["seed", "enricher"])
                .map_elements(_fuzzy_match, return_dtype=pl.Boolean)
                .alias("match")
            )
            .to_series()
        )
        return result

    def _compare_numeric(
        self,
        df: pl.DataFrame,
        seed_col: str,
        enricher_col: str,
        tolerance: float,
    ) -> pl.Series:
        """Numeric comparison with relative tolerance.

        |seed - enricher| / max(|seed|, 1) <= tolerance
        """
        import polars as pl

        s = df[seed_col].cast(pl.Float64, strict=False)
        e = df[enricher_col].cast(pl.Float64, strict=False)

        # Absolute difference / max(|seed|, 1)
        diff = (s - e).abs()
        denominator = s.abs().zip_with(s.abs() > 1.0, pl.Series([1.0] * len(df)))
        # Simpler: use pl.max_horizontal
        denom = (
            pl.DataFrame({"a": s.abs(), "b": pl.Series([1.0] * len(df))})
            .select(pl.max_horizontal("a", "b"))
            .to_series()
        )

        relative_diff = diff / denom

        # Match if relative diff <= tolerance (or either is null)
        return (relative_diff <= tolerance) | s.is_null() | e.is_null()

    @staticmethod
    def _parse_pipeline(pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        parts = pipeline.split("_", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        return parts[0], parts[1]
