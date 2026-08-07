"""Finalize and nullify collaborators for enrichment cross-validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.cross_validator_helpers import _combine_cv_details
from bioetl.domain.composite.cross_validation import CrossValidationStats

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.cross_validation import EnricherCVStats
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "finalize_cross_validation",
    "nullify_enricher_columns",
    "parse_pipeline_name",
]


def parse_pipeline_name(pipeline: str) -> tuple[str, str]:
    """Parse 'provider_entity' into (provider, entity)."""
    parts = pipeline.split("_", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
        )
    return parts[0], parts[1]


def nullify_enricher_columns(
    *,
    df: pl.DataFrame,
    is_error: pl.Series,
    enricher_provider: str,
    enricher_entity: str,
    enricher_pipeline: str,
    logger: LoggerPort,
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
    logger.info(
        "Nullified enricher columns for error records",
        enricher=enricher_pipeline,
        columns_nullified=len(cols),
        records_affected=int(is_error.sum()),
    )
    return df


def finalize_cross_validation(
    *,
    df: pl.DataFrame,
    enricher_error_counts: pl.Series,
    has_warning: pl.Series,
    enricher_stats_list: list[EnricherCVStats],
    enricher_details: list[pl.Series],
    total_records: int,
    quarantine_threshold: int,
    logger: LoggerPort,
) -> tuple[pl.DataFrame, CrossValidationStats]:
    """Add CV metadata columns and compute aggregate stats."""
    is_quarantine = enricher_error_counts >= quarantine_threshold
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
        logger.warning(
            "Seed records quarantined due to multiple enricher errors",
            quarantine_count=quarantine_count,
            threshold=quarantine_threshold,
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
    logger.info(
        "Cross-validation completed",
        total=total_records,
        passed=passed_count,
        warned=warned_count,
        errored=errored_count,
        quarantined=quarantine_count,
    )
    return df, stats
