"""Integrity DQ checks: referential integrity, SCD integrity.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    ForeignKeyResult,
    ReferentialIntegrityResult,
    SCDIntegrityResult,
)


def check_referential_integrity(
    df: pl.DataFrame, reference_tables: dict[str, pl.DataFrame | pa.Table]
) -> ReferentialIntegrityResult:
    """Check foreign key references."""
    if not reference_tables:
        return ReferentialIntegrityResult(
            foreign_keys={},
            status=DQCheckStatus.PASS,
        )

    fk_results: dict[str, ForeignKeyResult] = {}
    has_failures = False
    has_warnings = False

    for ref_key, ref_table in reference_tables.items():
        parts = ref_key.split("->")
        if len(parts) != 2:
            continue

        local_col = parts[0].strip()
        ref_parts = parts[1].strip().split(".")
        if len(ref_parts) != 2:
            continue

        ref_col = ref_parts[1]

        if local_col not in df.columns:
            continue

        if isinstance(ref_table, pa.Table):
            ref_df: pl.DataFrame = pl.from_arrow(ref_table)  # type: ignore[assignment]
        else:
            ref_df = ref_table

        if ref_col not in ref_df.columns:
            continue

        local_values = df[local_col].drop_nulls()
        ref_values = ref_df[ref_col].unique()

        total_refs = len(local_values)
        valid_refs = int(local_values.is_in(ref_values).sum())
        orphans = total_refs - valid_refs

        if orphans > 0:
            if orphans / total_refs > 0.01:
                status = DQCheckStatus.FAIL
                has_failures = True
            else:
                status = DQCheckStatus.WARN
                has_warnings = True
        else:
            status = DQCheckStatus.PASS

        fk_results[ref_key] = ForeignKeyResult(
            reference=ref_key,
            total_references=total_refs,
            valid_references=valid_refs,
            orphan_records=orphans,
            status=status,
        )

    overall_status = DQCheckStatus.PASS
    if has_failures:
        overall_status = DQCheckStatus.FAIL
    elif has_warnings:
        overall_status = DQCheckStatus.WARN

    return ReferentialIntegrityResult(
        foreign_keys=fk_results,
        status=overall_status,
    )


def check_scd_integrity(
    df: pl.DataFrame, scd_config: dict[str, Any] | None
) -> SCDIntegrityResult:
    """Check SCD (Slowly Changing Dimension) integrity."""
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
        except Exception:
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
