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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    CrossValidationStats,
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


@dataclass
class _EnricherValidationResult:
    """Internal result from validating one enricher against seed."""

    stats: EnricherCVStats
    is_error: pl.Series  # Boolean series: True where enricher error
    is_warning: pl.Series  # Boolean series: True where warning
    df: pl.DataFrame  # Potentially modified DataFrame (nullified columns)
    detail: pl.Series  # JSON string per row, null where no mismatches


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

        # Track per-row aggregates across all enrichers
        enricher_error_counts = pl.Series("_ee", [0] * total_records, dtype=pl.Int32)
        has_warning = pl.Series("_hw", [False] * total_records, dtype=pl.Boolean)
        enricher_stats_list: list[EnricherCVStats] = []
        enricher_details: list[pl.Series] = []

        for enricher_pipeline in enricher_pipelines:
            pairing = self._config.get_pairing(enricher_pipeline)
            if pairing is None:
                continue

            result = self._validate_enricher(
                merged_df, pairing, seed_provider, seed_entity, enricher_pipeline
            )
            merged_df = result.df
            enricher_stats_list.append(result.stats)
            enricher_error_counts = enricher_error_counts + result.is_error.cast(
                pl.Int32
            )
            has_warning = has_warning | result.is_warning
            enricher_details.append(result.detail)

        # Add CV metadata and build stats
        merged_df, stats = self._finalize(
            merged_df,
            enricher_error_counts,
            has_warning,
            enricher_stats_list,
            enricher_details,
            total_records,
            seed_provider,
            seed_entity,
        )
        return merged_df, stats

    def _validate_enricher(
        self,
        df: pl.DataFrame,
        pairing: EnricherFieldPairing,
        seed_provider: str,
        seed_entity: str,
        enricher_pipeline: str,
    ) -> _EnricherValidationResult:
        """Validate a single enricher against seed fields.

        Returns validation result with per-row verdicts and optionally
        nullified enricher columns.
        """

        enricher_provider, enricher_entity = self._parse_pipeline(enricher_pipeline)
        total = len(df)

        mismatch_count, _, field_mismatches, field_mismatch_bools = (
            self._count_mismatches_vectorized(
                df,
                pairing,
                seed_provider,
                seed_entity,
                enricher_provider,
                enricher_entity,
            )
        )

        is_error = mismatch_count >= self._config.error_threshold
        is_warning = (mismatch_count >= self._config.warning_threshold) & ~is_error

        error_count = int(is_error.sum())
        warn_count = int(is_warning.sum())
        pass_count = total - error_count - warn_count

        self._logger.info(
            "Cross-validation for enricher",
            enricher=enricher_pipeline,
            passed=pass_count,
            warned=warn_count,
            errored=error_count,
            field_mismatches=field_mismatches,
        )

        # Null enricher columns where ENRICHER_ERROR
        if error_count > 0:
            df = self._nullify_enricher_columns(
                df, is_error, enricher_provider, enricher_entity, enricher_pipeline
            )

        field_mismatches_tuple = tuple(field_mismatches.items())

        # Build per-row detail JSON for this enricher
        detail = _build_enricher_detail(
            enricher_pipeline, field_mismatch_bools, mismatch_count
        )

        return _EnricherValidationResult(
            stats=EnricherCVStats(
                enricher=enricher_pipeline,
                total_records=total,
                passed=pass_count,
                warned=warn_count,
                errored=error_count,
                field_mismatches=field_mismatches_tuple,
            ),
            is_error=is_error,
            is_warning=is_warning,
            df=df,
            detail=detail,
        )

    def _nullify_enricher_columns(
        self,
        df: pl.DataFrame,
        is_error: pl.Series,
        enricher_provider: str,
        enricher_entity: str,
        enricher_pipeline: str,
    ) -> pl.DataFrame:
        """Null all enricher-prefixed columns where is_error is True."""
        import polars as pl

        prefix = f"{enricher_provider}.{enricher_entity}."
        cols = [c for c in df.columns if c.startswith(prefix)]
        if not cols:
            return df

        df = df.with_columns(
            [
                pl.when(is_error).then(pl.lit(None)).otherwise(pl.col(c)).alias(c)
                for c in cols
            ]
        )
        self._logger.info(
            "Nullified enricher columns for error records",
            enricher=enricher_pipeline,
            columns_nullified=len(cols),
            records_affected=int(is_error.sum()),
        )
        return df

    def _finalize(
        self,
        df: pl.DataFrame,
        enricher_error_counts: pl.Series,
        has_warning: pl.Series,
        enricher_stats_list: list[EnricherCVStats],
        enricher_details: list[pl.Series],
        total_records: int,
        seed_provider: str,
        seed_entity: str,
    ) -> tuple[pl.DataFrame, CrossValidationStats]:
        """Add CV metadata columns and compute aggregate stats."""
        is_quarantine = enricher_error_counts >= self._config.quarantine_threshold
        quarantine_count = int(is_quarantine.sum())
        cv_details = _combine_cv_details(enricher_details, total_records)

        df = df.with_columns(
            [
                has_warning.alias("_cv_warn"),
                (enricher_error_counts > 0).alias("_cv_error"),
                is_quarantine.alias("_cv_quarantine"),
                cv_details.alias("_cv_details"),
            ]
        )
        if quarantine_count > 0:
            self._logger.warning(
                "Seed records quarantined due to multiple enricher errors",
                quarantine_count=quarantine_count,
                threshold=self._config.quarantine_threshold,
            )
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
        return df, stats

    def _count_mismatches_vectorized(
        self,
        df: pl.DataFrame,
        pairing: EnricherFieldPairing,
        seed_provider: str,
        seed_entity: str,
        enricher_provider: str,
        enricher_entity: str,
    ) -> tuple[pl.Series, pl.Series, dict[str, int], dict[str, pl.Series]]:
        """Count field mismatches per row using vectorized Polars operations.

        Returns:
            Tuple of (mismatch_count Series, compared_count Series,
            per-field mismatch counts dict, per-field boolean mismatch Series).
        """
        import polars as pl

        n = len(df)
        mismatch_total = pl.Series("_mm", [0] * n, dtype=pl.Int32)
        compared_total = pl.Series("_cmp", [0] * n, dtype=pl.Int32)
        field_mismatch_counts: dict[str, int] = {}
        field_mismatch_bools: dict[str, pl.Series] = {}

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

            both_present = _both_non_empty_mask(df, seed_col, enricher_col)
            compared_total = compared_total + both_present.cast(pl.Int32)

            match_result = self._compare_field(
                df, seed_col, enricher_col, spec.method, spec.threshold
            )
            is_mismatch = both_present & ~match_result
            mismatch_total = mismatch_total + is_mismatch.cast(pl.Int32)
            field_mismatch_counts[spec.field_name] = int(is_mismatch.sum())
            field_mismatch_bools[spec.field_name] = is_mismatch

        return (
            mismatch_total,
            compared_total,
            field_mismatch_counts,
            field_mismatch_bools,
        )

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
        """
        import polars as pl

        if method == ComparisonMethod.EXACT:
            return _compare_exact(df, seed_col, enricher_col)
        elif method == ComparisonMethod.FUZZY:
            return _compare_fuzzy(df, seed_col, enricher_col, threshold)
        elif method == ComparisonMethod.NUMERIC_TOLERANCE:
            return _compare_numeric(df, seed_col, enricher_col, threshold)
        else:
            return pl.Series([True] * len(df))

    @staticmethod
    def _parse_pipeline(pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        parts = pipeline.split("_", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        return parts[0], parts[1]


# --- Module-level helpers (extracted to reduce class size) ---


def _build_enricher_detail(
    enricher_pipeline: str,
    field_mismatch_bools: dict[str, pl.Series],
    mismatch_count: pl.Series,
) -> pl.Series:
    """Build per-row JSON detail string for one enricher.

    For rows with mismatches, produces JSON like:
    {"enricher": "crossref_publication", "field_mismatches": ["title", "volume"]}

    Returns null for rows with no mismatches.
    """
    import json

    import polars as pl

    n = len(mismatch_count)
    if not field_mismatch_bools:
        return pl.Series("_detail", [None] * n, dtype=pl.String)

    bool_df = pl.DataFrame(field_mismatch_bools)

    def _row_to_json(row: dict) -> str | None:  # type: ignore[type-arg]
        fields = [f for f, v in row.items() if v]
        if not fields:
            return None
        return json.dumps(
            {"enricher": enricher_pipeline, "field_mismatches": fields},
            ensure_ascii=False,
        )

    return bool_df.select(
        pl.struct(bool_df.columns)
        .map_elements(_row_to_json, return_dtype=pl.String)
        .alias("_detail")
    ).to_series()


def _combine_cv_details(
    enricher_details: list[pl.Series], total_records: int
) -> pl.Series:
    """Combine per-enricher detail series into a single _cv_details column.

    Merges non-null detail JSON objects from each enricher into a JSON array
    per row. Returns null for rows with no mismatches across any enricher.

    Example output per row:
    [{"enricher": "crossref_publication", "field_mismatches": ["title"]},
     {"enricher": "pubmed_publication", "field_mismatches": ["volume"]}]
    """
    import json

    import polars as pl

    if not enricher_details:
        return pl.Series("_cv_details", [None] * total_records, dtype=pl.String)

    cols = {f"_d{i}": s for i, s in enumerate(enricher_details)}
    detail_df = pl.DataFrame(cols)

    def _merge_row(row: dict) -> str | None:  # type: ignore[type-arg]
        parts = [v for v in row.values() if v is not None]
        if not parts:
            return None
        items = [json.loads(p) for p in parts]
        return json.dumps(items, ensure_ascii=False)

    return detail_df.select(
        pl.struct(detail_df.columns)
        .map_elements(_merge_row, return_dtype=pl.String)
        .alias("_cv_details")
    ).to_series()


def _both_non_empty_mask(
    df: pl.DataFrame, seed_col: str, enricher_col: str
) -> pl.Series:
    """Create mask where both columns are non-null and non-empty."""
    import polars as pl

    mask = df[seed_col].is_not_null() & df[enricher_col].is_not_null()
    for col in (seed_col, enricher_col):
        dtype = df[col].dtype
        if dtype == pl.String or dtype == pl.Utf8:
            mask = mask & (df[col].str.len_chars() > 0)
    return mask


def _compare_exact(df: pl.DataFrame, seed_col: str, enricher_col: str) -> pl.Series:
    """Exact comparison after stripping whitespace."""
    import polars as pl

    s = df[seed_col].cast(pl.String).str.strip_chars()
    e = df[enricher_col].cast(pl.String).str.strip_chars()
    return s.eq(e) | s.is_null() | e.is_null()


def _compare_fuzzy(
    df: pl.DataFrame,
    seed_col: str,
    enricher_col: str,
    threshold: float,
) -> pl.Series:
    """Fuzzy comparison using Jaccard similarity on word sets."""
    import polars as pl

    def _fuzzy_match(row: dict) -> bool:  # type: ignore[type-arg]
        s_val = row["seed"]
        e_val = row["enricher"]
        if s_val is None or e_val is None:
            return True
        return jaccard_similarity(str(s_val), str(e_val)) >= threshold

    return (
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


def _compare_numeric(
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
    diff = (s - e).abs()
    denom = (
        pl.DataFrame({"a": s.abs(), "b": pl.Series([1.0] * len(df))})
        .select(pl.max_horizontal("a", "b"))
        .to_series()
    )
    relative_diff = diff / denom
    return (relative_diff <= tolerance) | s.is_null() | e.is_null()
