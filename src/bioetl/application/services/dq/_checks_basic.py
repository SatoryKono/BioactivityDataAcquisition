"""Basic Gold DQ checks: record count, completeness, data freshness.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

__all__ = [
    "FRESHNESS_CRITICAL_HOURS",
    "FRESHNESS_WARNING_HOURS",
    "check_completeness",
    "check_data_freshness",
    "check_record_count",
]


from datetime import UTC, datetime

import polars as pl

from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldRejectReason,
    GoldRejectReasonCode,
    build_gold_contract_reject_reason,
)
from bioetl.domain.value_objects.dq_report import (
    CompletenessResult,
    DataFreshnessResult,
    DQCheckStatus,
    RecordCountResult,
)

# Freshness thresholds from RULES.md §3.4.1
FRESHNESS_WARNING_HOURS = 24
FRESHNESS_CRITICAL_HOURS = 72
_FRESHNESS_COLUMN_ERRORS = (
    pl.exceptions.PolarsError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)


def check_record_count(
    df: pl.DataFrame, baseline_stats: dict[str, object] | None
) -> RecordCountResult:
    """Check record count against baseline.

    Args:
        df: Input DataFrame.
        baseline_stats: Baseline stats.

    Returns:
        Check result as RecordCountResult.
    """
    current = len(df)
    baseline = (
        baseline_stats.get("record_count_ma30", current) if baseline_stats else current
    )
    if not isinstance(baseline, (int, float)):
        baseline = current
    delta = (current - baseline) / baseline if baseline > 0 else 0.0

    status = DQCheckStatus.PASS
    if delta < -0.5:
        status = DQCheckStatus.FAIL
    elif delta < -0.3:
        status = DQCheckStatus.WARN

    return RecordCountResult(
        value=current,
        status=status,
        delta_from_last_run=int(current - baseline) if baseline else None,
    )


def check_completeness(
    df: pl.DataFrame,
    required_fields: list[str],
    threshold: float,
    *,
    contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
) -> CompletenessResult:
    """Check completeness of required fields.

    Args:
        df: Input DataFrame.
        required_fields: Required fields.
        threshold: Threshold value.
        contract_version: Gold contract version used for reject payloads.

    Returns:
        Check result as CompletenessResult.
    """
    if not required_fields:
        return CompletenessResult(
            required_fields={},
            overall_completeness_score=1.0,
            minimum_threshold=threshold,
            status=DQCheckStatus.PASS,
        )

    field_rates: dict[str, float] = {}
    total_rate = 0.0
    count = 0

    for field in required_fields:
        if field in df.columns:
            null_count = df[field].null_count()
            rate = 1.0 - (null_count / len(df)) if len(df) > 0 else 0.0
            field_rates[field] = round(rate, 4)
            total_rate += rate
            count += 1
        else:
            field_rates[field] = 0.0

    overall_score = total_rate / count if count > 0 else 0.0

    status = DQCheckStatus.PASS if overall_score >= threshold else DQCheckStatus.FAIL
    reject_reasons: tuple[GoldRejectReason, ...] = ()
    if status == DQCheckStatus.FAIL:
        reject_reasons = tuple(
            build_gold_contract_reject_reason(
                reason_code=GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE,
                contract_version=contract_version,
                rule_id=f"gold.contract.required.{field}",
                field=field,
                message="Gold required-field completeness failed",
                details={
                    "completeness_rate": rate,
                    "minimum_threshold": threshold,
                },
            )
            for field, rate in field_rates.items()
            if rate < threshold
        )

    return CompletenessResult(
        required_fields=field_rates,
        overall_completeness_score=round(overall_score, 4),
        minimum_threshold=threshold,
        status=status,
        reject_reasons=reject_reasons,
    )


def check_data_freshness(
    df: pl.DataFrame, current_time: datetime
) -> DataFreshnessResult:
    """Check data freshness based on timestamp columns.

    Args:
        df: Input DataFrame.
        current_time: Current time.

    Returns:
        Check result as DataFreshnessResult.
    """
    max_ts = _extract_freshness_timestamp(df)

    if max_ts is None:
        return DataFreshnessResult(
            max_updated_at=None,
            freshness_lag_seconds=0.0,
            freshness_lag_hours=0.0,
            status=DQCheckStatus.PASS,
        )

    normalized_current_time = _as_utc_datetime(current_time)
    normalized_max_ts = _as_utc_datetime(max_ts)
    lag_seconds = (normalized_current_time - normalized_max_ts).total_seconds()
    lag_hours = lag_seconds / 3600

    if lag_hours > FRESHNESS_CRITICAL_HOURS:
        status = DQCheckStatus.FAIL
    elif lag_hours > FRESHNESS_WARNING_HOURS:
        status = DQCheckStatus.WARN
    else:
        status = DQCheckStatus.PASS

    return DataFreshnessResult(
        max_updated_at=normalized_max_ts,
        freshness_lag_seconds=round(lag_seconds, 2),
        freshness_lag_hours=round(lag_hours, 2),
        status=status,
    )


def _extract_freshness_timestamp(df: pl.DataFrame) -> datetime | None:
    """Return the first usable max timestamp from the standard freshness columns."""
    for col in ["_updated_at", "updated_at", "_ingestion_ts", "created_at"]:
        if col not in df.columns:
            continue
        try:
            col_max = df[col].max()
        except _FRESHNESS_COLUMN_ERRORS:
            continue
        if isinstance(col_max, datetime):
            return col_max
    return None


def _as_utc_datetime(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
