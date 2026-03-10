"""Silver DQ check implementations."""

from __future__ import annotations

import polars as pl

from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    DriftLevel,
    NullRateResult,
    RecordCountResult,
    SchemaDriftResult,
    TypeConformanceResult,
    UniquenessResult,
)

_SILVER_PROFILE_ERRORS = (
    pl.exceptions.PolarsError,
    ValueError,
    TypeError,
    RuntimeError,
)


class SilverDQChecksService:
    """Provide single-check evaluation methods for Silver DQ."""

    def check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[dict[str, object]],
    ) -> dict[str, object]:
        violations: list[dict[str, object]] = []
        for rule in key_nullability_rules:
            if bool(rule.get("nullable", False)):
                continue
            field = str(rule.get("field", ""))
            key_type = str(rule.get("key_type", "merge"))
            if field not in df.columns:
                continue
            null_count = int(df[field].null_count())
            if null_count > 0:
                violations.append(
                    {"field": field, "key_type": key_type, "null_count": null_count}
                )

        status = DQCheckStatus.FAIL if violations else DQCheckStatus.PASS
        return {
            "status": status.value,
            "violations": violations,
            "rules_checked": len(key_nullability_rules),
        }

    def check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        output_count = len(df)
        input_records = input_count or (output_count + quarantined_count)
        quarantine_rate = (
            quarantined_count / input_records if input_records > 0 else 0.0
        )
        status = DQCheckStatus.WARN if quarantine_rate > 0.1 else DQCheckStatus.PASS

        return RecordCountResult(
            value=output_count,
            status=status,
            input_records=input_records,
            output_records=output_count,
            quarantined_records=quarantined_count,
            quarantine_rate=round(quarantine_rate, 4),
        )

    def check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        results: list[NullRateResult] = []
        total_nulls = 0
        total_cells = 0

        for col in df.columns:
            null_count = df[col].null_count()
            total = len(df)
            null_rate = null_count / total if total > 0 else 0.0
            total_nulls += null_count
            total_cells += total
            status = DQCheckStatus.WARN if null_rate > 0.5 else DQCheckStatus.PASS
            results.append(
                NullRateResult(
                    column_name=col,
                    null_rate=round(null_rate, 4),
                    status=status,
                )
            )

        overall_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
        return results, round(overall_null_rate, 4)

    def check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        if not primary_keys:
            return UniquenessResult(
                primary_key="",
                unique_count=len(df),
                total_count=len(df),
                duplicate_rate=0.0,
                status=DQCheckStatus.PASS,
            )

        existing_keys = [k for k in primary_keys if k in df.columns]
        if not existing_keys:
            return UniquenessResult(
                primary_key=",".join(primary_keys),
                unique_count=len(df),
                total_count=len(df),
                duplicate_rate=0.0,
                status=DQCheckStatus.WARN,
                column_stats={"_note": {"message": "Primary key columns not found"}},
            )

        unique_count = df.select(existing_keys).unique().height
        total_count = len(df)
        duplicate_rate = (
            (total_count - unique_count) / total_count if total_count else 0.0
        )

        column_stats: dict[str, dict[str, float | int]] = {}
        for col in df.columns[:10]:
            try:
                cardinality = df[col].n_unique()
                column_stats[col] = {
                    "cardinality": cardinality,
                    "uniqueness_ratio": round(cardinality / len(df), 4)
                    if len(df)
                    else 0.0,
                }
            except _SILVER_PROFILE_ERRORS:
                pass

        return UniquenessResult(
            primary_key=",".join(existing_keys),
            unique_count=unique_count,
            total_count=total_count,
            duplicate_rate=round(duplicate_rate, 4),
            column_stats=column_stats,
            status=DQCheckStatus.PASS if duplicate_rate == 0 else DQCheckStatus.WARN,
        )

    def check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        errors = tuple(
            f"Column {col} has mixed types (Object)"
            for col in df.columns
            if df[col].dtype == pl.Object
        )

        return TypeConformanceResult(
            schema_version=None,
            pandera_passed=len(errors) == 0,
            errors=errors,
            type_coercions={},
            status=DQCheckStatus.PASS if not errors else DQCheckStatus.WARN,
        )

    def check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        current_schema = {col: str(df[col].dtype) for col in df.columns}

        if previous_schema is None:
            return SchemaDriftResult(
                drift_level=DriftLevel.INFO, status=DQCheckStatus.PASS
            )

        new_fields = [f for f in current_schema if f not in previous_schema]
        missing_fields = [f for f in previous_schema if f not in current_schema]
        type_changes = tuple(
            {
                "field": field,
                "from": previous_schema[field],
                "to": current_schema[field],
            }
            for field in current_schema
            if field in previous_schema
            and current_schema[field] != previous_schema[field]
        )

        drift_level = (
            DriftLevel.CRITICAL if (missing_fields or type_changes) else DriftLevel.INFO
        )
        status = (
            DQCheckStatus.WARN
            if drift_level == DriftLevel.CRITICAL
            else DQCheckStatus.PASS
        )

        return SchemaDriftResult(
            drift_level=drift_level,
            new_fields=tuple(new_fields),
            missing_fields=tuple(missing_fields),
            type_changes=type_changes,
            status=status,
        )

    def check_deduplication(
        self,
        df: pl.DataFrame,
        input_count: int,
    ) -> DeduplicationStatsResult:
        output_count = len(df)
        dedupe_count = input_count - output_count

        content_hash_dupes = 0
        if "_content_hash" in df.columns:
            content_hash_dupes = output_count - df["_content_hash"].n_unique()

        return DeduplicationStatsResult(
            input_before_dedupe=input_count,
            duplicates_by_content_hash=content_hash_dupes,
            duplicates_by_business_key=dedupe_count - content_hash_dupes,
            output_after_dedupe=output_count,
            status=DQCheckStatus.PASS,
        )

    def check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        if "_content_hash" not in df.columns:
            return ContentHashIntegrityResult(
                records_checked=0,
                hash_collisions=0,
                rehash_mismatches=0,
                status=DQCheckStatus.PASS,
            )

        duplicates = df["_content_hash"].value_counts().filter(pl.col("count") > 1)
        hash_collisions = len(duplicates)
        return ContentHashIntegrityResult(
            records_checked=len(df),
            hash_collisions=hash_collisions,
            rehash_mismatches=0,
            status=DQCheckStatus.PASS if hash_collisions == 0 else DQCheckStatus.WARN,
        )


__all__ = ["SilverDQChecksService"]
