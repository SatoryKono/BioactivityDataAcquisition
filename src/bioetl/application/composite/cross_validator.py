"""Enrichment cross-validator for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.cross_validator_helpers import (
    _build_enricher_detail,
    _count_mismatches_vectorized,
)
from bioetl.application.composite.helpers.cross_validator_finalize import (
    finalize_cross_validation,
    nullify_enricher_columns,
    parse_pipeline_name,
)
from bioetl.domain.composite.cross_validation import (
    CrossValidationStats,
    EnricherCVStats,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite import (
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

        seed_provider, seed_entity = parse_pipeline_name(seed_pipeline)
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
        return finalize_cross_validation(
            df=merged_df,
            enricher_error_counts=enricher_error_counts,
            has_warning=has_warning,
            enricher_stats_list=enricher_stats_list,
            enricher_details=enricher_details,
            total_records=total_records,
            quarantine_threshold=self._config.quarantine_threshold,
            logger=self._logger,
        )

    def _validate_enricher(
        self,
        df: pl.DataFrame,
        pairing: EnricherFieldPairing,
        seed_provider: str,
        seed_entity: str,
        enricher_pipeline: str,
    ) -> _EnricherValidationResult:
        """Validate a single enricher against seed fields."""

        enricher_provider, enricher_entity = parse_pipeline_name(enricher_pipeline)
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
            df = nullify_enricher_columns(
                df=df,
                is_error=is_error,
                enricher_provider=enricher_provider,
                enricher_entity=enricher_entity,
                enricher_pipeline=enricher_pipeline,
                logger=self._logger,
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

    @staticmethod
    def _parse_pipeline(pipeline: str) -> tuple[str, str]:
        """Parse 'provider_entity' into (provider, entity)."""
        return parse_pipeline_name(pipeline)
