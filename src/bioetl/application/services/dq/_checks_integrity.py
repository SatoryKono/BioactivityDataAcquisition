"""Integrity DQ checks: referential integrity, SCD integrity.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

__all__ = ["check_referential_integrity", "check_scd_integrity"]


from collections.abc import Mapping
from typing import cast

import polars as pl
import pyarrow as pa

from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldRejectReasonCode,
    ScdConfig,
    build_gold_contract_reject_reason,
)
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    ForeignKeyResult,
    ReferentialIntegrityResult,
    SCDIntegrityResult,
)

_SCD_INTEGRITY_ERRORS = (
    pl.exceptions.PolarsError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)


def _build_default_scd_result(
    *,
    scd_type: int,
    total_entities: int,
) -> SCDIntegrityResult:
    """Return default PASS result for missing/disabled SCD checks."""
    return SCDIntegrityResult(
        scd_type=scd_type,
        total_entities=total_entities,
        entities_with_history=0,
        avg_versions_per_entity=1.0,
        version_gaps=0,
        temporal_conflicts=0,
        overlapping_validity_periods=0,
        status=DQCheckStatus.PASS,
    )


def _count_scd_overlaps(
    *,
    df: pl.DataFrame,
    entity_key: str,
    valid_from: str,
    valid_to: str,
) -> int:
    """Count overlapping SCD validity periods for a bounded entity sample."""
    overlaps = 0
    try:
        for entity in df[entity_key].unique().to_list()[:100]:
            entity_records = df.filter(pl.col(entity_key) == entity).sort(valid_from)
            if len(entity_records) <= 1:
                continue
            for index in range(len(entity_records) - 1):
                current_to = entity_records[valid_to][index]
                next_from = entity_records[valid_from][index + 1]
                if (
                    current_to is not None
                    and next_from is not None
                    and current_to > next_from
                ):
                    overlaps += 1
    except _SCD_INTEGRITY_ERRORS:
        # Skip malformed partitions during overlap analysis.
        return overlaps
    return overlaps


def _materialize_entity_key(
    df: pl.DataFrame,
    *,
    entity_keys: tuple[str, ...],
) -> tuple[pl.DataFrame, str]:
    """Build a single grouping key for simple and composite business keys."""
    if len(entity_keys) == 1:
        return df, entity_keys[0]
    return df.with_columns(
        pl.struct(list(entity_keys)).alias("__scd_entity_key")
    ), "__scd_entity_key"


def _parse_reference_key(ref_key: str) -> tuple[str, str] | None:
    """Parse mapping key ``local_col -> table.ref_col``."""
    parts = ref_key.split("->")
    if len(parts) != 2:
        return None
    local_col = parts[0].strip()
    ref_parts = parts[1].strip().split(".")
    if len(ref_parts) != 2:
        return None
    return local_col, ref_parts[1]


def _as_reference_dataframe(ref_table: pl.DataFrame | pa.Table) -> pl.DataFrame:
    """Convert reference table to Polars DataFrame."""
    if isinstance(ref_table, pa.Table):
        return cast("pl.DataFrame", pl.from_arrow(ref_table))
    return ref_table


def _classify_fk_status(orphan_records: int, total_references: int) -> DQCheckStatus:
    """Classify FK integrity status from orphan ratio."""
    if orphan_records <= 0:
        return DQCheckStatus.PASS
    orphan_ratio = orphan_records / total_references if total_references > 0 else 0.0
    return DQCheckStatus.FAIL if orphan_ratio > 0.01 else DQCheckStatus.WARN


def _build_fk_result(
    df: pl.DataFrame,
    ref_key: str,
    local_col: str,
    ref_df: pl.DataFrame,
    ref_col: str,
    *,
    contract_version: str | None,
) -> ForeignKeyResult:
    """Compute foreign-key metrics for one mapping rule."""
    local_values = df[local_col].drop_nulls()
    ref_values = ref_df[ref_col].unique()

    total_refs = len(local_values)
    valid_refs = int(local_values.is_in(ref_values.implode()).sum())
    orphans = total_refs - valid_refs
    status = _classify_fk_status(orphans, total_refs)
    reject_reason = (
        build_gold_contract_reject_reason(
            reason_code=GoldRejectReasonCode.CONTRACT_REFERENCE_FAILURE,
            contract_version=contract_version,
            rule_id=f"gold.contract.reference.{local_col}.{ref_col}",
            field=local_col,
            message="Gold referential integrity check found orphan references",
            details={
                "reference": ref_key,
                "total_references": total_refs,
                "valid_references": valid_refs,
                "orphan_records": orphans,
            },
        )
        if orphans > 0
        else None
    )

    return ForeignKeyResult(
        reference=ref_key,
        total_references=total_refs,
        valid_references=valid_refs,
        orphan_records=orphans,
        status=status,
        reject_reason=reject_reason,
    )


def _aggregate_dq_status(statuses: list[DQCheckStatus]) -> DQCheckStatus:
    """Aggregate statuses with FAIL > WARN > PASS precedence."""
    if any(status == DQCheckStatus.FAIL for status in statuses):
        return DQCheckStatus.FAIL
    if any(status == DQCheckStatus.WARN for status in statuses):
        return DQCheckStatus.WARN
    return DQCheckStatus.PASS


def check_referential_integrity(
    df: pl.DataFrame,
    reference_tables: dict[str, pl.DataFrame | pa.Table],
    *,
    contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
) -> ReferentialIntegrityResult:
    """Check foreign key references.

    Args:
        df: Input DataFrame.
        reference_tables: Reference tables.
        contract_version: Gold contract version used for reject payloads.

    Returns:
        Check result as ReferentialIntegrityResult.
    """
    if not reference_tables:
        return ReferentialIntegrityResult(
            foreign_keys={},
            status=DQCheckStatus.PASS,
        )

    fk_results: dict[str, ForeignKeyResult] = {}

    for ref_key, ref_table in reference_tables.items():
        parsed_ref = _parse_reference_key(ref_key)
        if parsed_ref is None:
            continue
        local_col, ref_col = parsed_ref

        if local_col not in df.columns:
            continue

        ref_df = _as_reference_dataframe(ref_table)
        if ref_col not in ref_df.columns:
            continue

        fk_results[ref_key] = _build_fk_result(
            df=df,
            ref_key=ref_key,
            local_col=local_col,
            ref_df=ref_df,
            ref_col=ref_col,
            contract_version=contract_version,
        )

    return ReferentialIntegrityResult(
        foreign_keys=fk_results,
        status=_aggregate_dq_status([result.status for result in fk_results.values()]),
    )


def _normalize_scd_config(
    df: pl.DataFrame,
    scd_config: ScdConfig | Mapping[str, object] | None,
) -> ScdConfig | None:
    """Normalize and validate SCD config. Returns None when defaults apply."""
    normalized = (
        ScdConfig.from_mapping(scd_config)
        if isinstance(scd_config, Mapping)
        else scd_config
    )
    if not normalized:
        return None
    entity_keys = normalized.business_keys
    if not entity_keys:
        return None
    if any(key not in df.columns for key in entity_keys):
        return None
    return normalized


def check_scd_integrity(
    df: pl.DataFrame,
    scd_config: ScdConfig | Mapping[str, object] | None,
) -> SCDIntegrityResult:
    """Check Slowly Changing Dimension (SCD) integrity metrics.

    Args:
        df: Input Polars DataFrame to check SCD validity on.
        scd_config: Typed SCD configuration with business key and validity
            column names. Pass None to return a
            default PASS result without checking.

    Returns:
        SCDIntegrityResult with entity counts, version statistics, and
        overlapping validity period count with a PASS or WARN status.
    """
    config = _normalize_scd_config(df, scd_config)
    scd_type = config.scd_type if config else 2
    if config is None:
        return _build_default_scd_result(
            scd_type=scd_type,
            total_entities=len(df),
        )

    entity_keys = config.business_keys
    valid_from = config.valid_from_col
    valid_to = config.valid_to_col

    analysis_df, entity_key = _materialize_entity_key(df, entity_keys=entity_keys)
    unique_entities = analysis_df[entity_key].n_unique()
    total_records = len(analysis_df)

    version_counts = analysis_df.group_by(entity_key).agg(pl.len().alias("versions"))
    entities_with_history = int((version_counts["versions"] > 1).sum())
    avg_versions = total_records / unique_entities if unique_entities > 0 else 1.0

    overlapping = (
        _count_scd_overlaps(
            df=analysis_df,
            entity_key=entity_key,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        if valid_from in analysis_df.columns and valid_to in analysis_df.columns
        else 0
    )

    return SCDIntegrityResult(
        scd_type=scd_type,
        total_entities=unique_entities,
        entities_with_history=entities_with_history,
        avg_versions_per_entity=round(avg_versions, 2),
        version_gaps=0,
        temporal_conflicts=0,
        overlapping_validity_periods=overlapping,
        status=DQCheckStatus.PASS if overlapping == 0 else DQCheckStatus.WARN,
    )
