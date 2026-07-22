"""Helper functions for enrichment cross-validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior.text_similarity import jaccard_similarity
from bioetl.domain.composite.cross_validation import ComparisonMethod

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.cross_validation import EnricherFieldPairing
    from bioetl.domain.ports import LoggerPort


def _count_mismatches_vectorized(
    df: pl.DataFrame,
    pairing: EnricherFieldPairing,
    seed_provider: str,
    seed_entity: str,
    enricher_provider: str,
    enricher_entity: str,
    *,
    logger: LoggerPort,
) -> tuple[pl.Series, pl.Series, dict[str, int], dict[str, pl.Series]]:
    """Count field mismatches per row using vectorized Polars operations."""
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
            logger.debug(
                "Skipping CV field - column not found",
                field=spec.field_name,
                seed_col=seed_col,
                enricher_col=enricher_col,
            )
            continue

        both_present = _both_non_empty_mask(df, seed_col, enricher_col)
        compared_total = compared_total + both_present.cast(pl.Int32)
        match_result = _compare_field(
            df,
            seed_col,
            enricher_col,
            spec.method,
            spec.threshold,
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
    df: pl.DataFrame,
    seed_col: str,
    enricher_col: str,
    method: ComparisonMethod,
    threshold: float,
) -> pl.Series:
    """Compare a single field between seed and enricher."""
    import polars as pl

    if method == ComparisonMethod.EXACT:
        return _compare_exact(df, seed_col, enricher_col)
    if method == ComparisonMethod.FUZZY:
        return _compare_fuzzy(df, seed_col, enricher_col, threshold)
    if method == ComparisonMethod.NUMERIC_TOLERANCE:
        return _compare_numeric(df, seed_col, enricher_col, threshold)
    return pl.Series([True] * len(df))


def _build_enricher_detail(
    enricher_pipeline: str,
    field_mismatch_bools: dict[str, pl.Series],
    mismatch_count: pl.Series,
) -> pl.Series:
    """Build per-row JSON detail string for one enricher."""
    import json

    import polars as pl

    n = len(mismatch_count)
    if not field_mismatch_bools:
        return pl.Series("_detail", [None] * n, dtype=pl.String)
    field_names = sorted(field_mismatch_bools)
    field_rows = [field_mismatch_bools[name].to_list() for name in field_names]
    details: list[str | None] = []

    for row_values in zip(*field_rows, strict=False):
        fields = [
            field_name
            for field_name, is_mismatch in zip(field_names, row_values, strict=False)
            if is_mismatch
        ]
        if not fields:
            details.append(None)
            continue
        details.append(
            json.dumps(
                {"enricher": enricher_pipeline, "field_mismatches": fields},
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    return pl.Series("_detail", details, dtype=pl.String)


def _combine_cv_details(
    enricher_details: list[pl.Series], total_records: int
) -> pl.Series:
    """Combine per-enricher detail series into a single _cv_details column."""
    import json

    import polars as pl

    if not enricher_details:
        return pl.Series("_cv_details", [None] * total_records, dtype=pl.String)
    detail_rows = [series.to_list() for series in enricher_details]
    merged_details: list[str | None] = []

    for row_values in zip(*detail_rows, strict=False):
        parts = [value for value in row_values if isinstance(value, str) and value]
        if not parts:
            merged_details.append(None)
            continue
        merged_details.append(
            json.dumps(
                [json.loads(part) for part in parts],
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    return pl.Series("_cv_details", merged_details, dtype=pl.String)


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

    def _fuzzy_match(row: dict[str, object]) -> bool:
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
    """Numeric comparison with relative tolerance."""
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


__all__ = [
    "_build_enricher_detail",
    "_combine_cv_details",
    "_compare_field",
    "_count_mismatches_vectorized",
]
