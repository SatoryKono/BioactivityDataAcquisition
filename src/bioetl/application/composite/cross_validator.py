"""Enrichment cross-validator for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.cross_validator_helpers import (
    _build_enricher_detail,
    _combine_cv_details,
    _count_mismatches_vectorized,
)
from bioetl.domain.composite.cross_validation import (
    CrossValidationStats,
    EnricherCVStats,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import (
        CrossValidationConfig,
        EnricherFieldPairing,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = ["EnrichmentCrossValidator"]


@dataclass
class _EnricherValidationResult:
    """Internal result from validating one enricher against seed."""

    stats: EnricherCVStats
    is_error: pl.Series  # Boolean series: True where enricher error
    is_warning: pl.Series  # Boolean series: True where warning
    df: pl.DataFrame  # Potentially modified DataFrame (nullified columns)
    detail: pl.Series  # JSON string per row, null where no mismatches


class EnrichmentCrossValidator:
    """Validates enricher data consistency against seed before merge."""

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
            merged_df: Merged DataFrame containing seed and enricher columns.
            enricher_pipelines: List of enricher pipeline names whose columns are validated.
            seed_pipeline: Pipeline name of the seed source used as the reference values.

        Returns:
            Tuple of (merged_df, CrossValidationStats) where merged_df may have enricher
            columns nullified for error records and CV metadata columns added.
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
        """Validate a single enricher against seed fields."""

        enricher_provider, enricher_entity = self._parse_pipeline(enricher_pipeline)
        total = len(df)

        mismatch_count, _, field_mismatches, field_mismatch_bools = (
            _count_mismatches_vectorized(
                df,
                pairing,
                seed_provider,
                seed_entity,
                enricher_provider,
                enricher_entity,
                logger=self._logger,
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
        del seed_provider, seed_entity
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

    @staticmethod
    def _parse_pipeline(pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        parts = pipeline.split("_", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        return parts[0], parts[1]
