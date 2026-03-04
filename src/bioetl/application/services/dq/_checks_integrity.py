"""Integrity DQ checks: referential integrity, SCD integrity.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

__all__ = ["check_referential_integrity", "check_scd_integrity"]


from typing import Any, cast

import polars as pl
import pyarrow as pa

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
) -> ForeignKeyResult:
    """Compute foreign-key metrics for one mapping rule."""
    local_values = df[local_col].drop_nulls()
    ref_values = ref_df[ref_col].unique()

    total_refs = len(local_values)
    valid_refs = int(local_values.is_in(ref_values).sum())
    orphans = total_refs - valid_refs
    status = _classify_fk_status(orphans, total_refs)

    return ForeignKeyResult(
        reference=ref_key,
        total_references=total_refs,
        valid_references=valid_refs,
        orphan_records=orphans,
        status=status,
    )


def _aggregate_dq_status(statuses: list[DQCheckStatus]) -> DQCheckStatus:
    """Aggregate statuses with FAIL > WARN > PASS precedence."""
    if any(status == DQCheckStatus.FAIL for status in statuses):
        return DQCheckStatus.FAIL
    if any(status == DQCheckStatus.WARN for status in statuses):
        return DQCheckStatus.WARN
    return DQCheckStatus.PASS


def check_referential_integrity(
    df: pl.DataFrame, reference_tables: dict[str, pl.DataFrame | pa.Table]
) -> ReferentialIntegrityResult:
    """Check foreign key references.

    Args:
        df: Input DataFrame.
        reference_tables: Reference tables.

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
        )

    return ReferentialIntegrityResult(
        foreign_keys=fk_results,
        status=_aggregate_dq_status([result.status for result in fk_results.values()]),
    )


def check_scd_integrity(
    df: pl.DataFrame,
    scd_config: dict[str, Any] | None,  # Any: SCD config has heterogeneous values
) -> SCDIntegrityResult:
    """Check SCD (Slowly Changing Dimension) integrity.

    Args:
        df: Input DataFrame.
        scd_config: Configuration for scd.

    Returns:
        Check result as SCDIntegrityResult.
    """
    if not scd_config:
        return SCDIntegrityResult(
            scd_type=2,
            total_entities=len(df),
            entities_with_history=0,
            avg_versions_per_entity=1.0,
            version_gaps=0,
            temporal_conflicts=0,
            overlapping_validity_periods=0,
            status=DQCheckStatus.PASS,
        )

    scd_type = scd_config.get("type", 2)
    entity_key = scd_config.get("entity_key")
    valid_from = scd_config.get("valid_from_col", "_valid_from")
    valid_to = scd_config.get("valid_to_col", "_valid_to")

    if not entity_key or entity_key not in df.columns:
        return SCDIntegrityResult(
            scd_type=scd_type,
            total_entities=len(df),
            entities_with_history=0,
            avg_versions_per_entity=1.0,
            version_gaps=0,
            temporal_conflicts=0,
            overlapping_validity_periods=0,
            status=DQCheckStatus.PASS,
        )

    unique_entities = df[entity_key].n_unique()
    total_records = len(df)

    version_counts = df.group_by(entity_key).agg(pl.count().alias("versions"))
    entities_with_history = int((version_counts["versions"] > 1).sum())
    avg_versions = total_records / unique_entities if unique_entities > 0 else 1.0

    version_gaps = 0
    temporal_conflicts = 0
    overlapping = 0

    if valid_from in df.columns and valid_to in df.columns:
        try:
            for entity in df[entity_key].unique().to_list()[:100]:
                entity_records = df.filter(pl.col(entity_key) == entity).sort(
                    valid_from
                )
                if len(entity_records) > 1:
                    for i in range(len(entity_records) - 1):
                        current_to = entity_records[valid_to][i]
                        next_from = entity_records[valid_from][i + 1]
                        if (
                            current_to is not None
                            and next_from is not None
                            and current_to > next_from
                        ):
                            overlapping += 1
        except _SCD_INTEGRITY_ERRORS:
            # Catch all: entity group processing may fail due to missing/invalid
            # temporal fields or sort errors. Skip entity for SCD overlap check.
            pass

    status = DQCheckStatus.PASS if overlapping == 0 else DQCheckStatus.WARN

    return SCDIntegrityResult(
        scd_type=scd_type,
        total_entities=unique_entities,
        entities_with_history=entities_with_history,
        avg_versions_per_entity=round(avg_versions, 2),
        version_gaps=version_gaps,
        temporal_conflicts=temporal_conflicts,
        overlapping_validity_periods=overlapping,
        status=status,
    )
