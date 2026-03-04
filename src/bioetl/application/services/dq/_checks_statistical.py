"""Statistical DQ checks: statistical profile, anomaly detection.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

__all__ = [
    "NULL_RATE_CRITICAL_MULTIPLIER",
    "NULL_RATE_WARNING_MULTIPLIER",
    "RECORD_COUNT_CRITICAL_THRESHOLD",
    "RECORD_COUNT_WARNING_THRESHOLD",
    "check_anomaly_detection",
    "check_statistical_profile",
]


import polars as pl

from bioetl.domain.value_objects.dq_report import (
    AnomalyDetectionResult,
    AnomalyMetric,
    DQCheckStatus,
    StatisticalMetric,
    StatisticalProfileResult,
)
from bioetl.domain.types import JsonDict

# Thresholds from RULES.md §3.4.1
NULL_RATE_WARNING_MULTIPLIER = 2.0
NULL_RATE_CRITICAL_MULTIPLIER = 5.0
RECORD_COUNT_WARNING_THRESHOLD = 0.70
RECORD_COUNT_CRITICAL_THRESHOLD = 0.50


def _null_rate_status(ratio: float) -> DQCheckStatus:
    if ratio > NULL_RATE_CRITICAL_MULTIPLIER:
        return DQCheckStatus.FAIL
    if ratio > NULL_RATE_WARNING_MULTIPLIER:
        return DQCheckStatus.WARN
    return DQCheckStatus.PASS


def _record_count_status(ratio: float) -> DQCheckStatus:
    if ratio < RECORD_COUNT_CRITICAL_THRESHOLD:
        return DQCheckStatus.FAIL
    if ratio < RECORD_COUNT_WARNING_THRESHOLD:
        return DQCheckStatus.WARN
    return DQCheckStatus.PASS


def _build_null_rate_metric(
    df: pl.DataFrame,
    baseline_stats: JsonDict,  # Any: heterogeneous baseline map
) -> StatisticalMetric | None:
    baseline_null_rate = baseline_stats.get("null_rate_ma30")
    if baseline_null_rate is None:
        return None

    total_nulls = sum(df[col].null_count() for col in df.columns)
    total_cells = len(df) * len(df.columns)
    current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
    ratio = current_null_rate / baseline_null_rate if baseline_null_rate > 0 else 1.0
    status = _null_rate_status(ratio)
    return StatisticalMetric(
        current=round(current_null_rate, 4),
        baseline=round(baseline_null_rate, 4),
        ratio=round(ratio, 4),
        threshold_warning=NULL_RATE_WARNING_MULTIPLIER,
        threshold_critical=NULL_RATE_CRITICAL_MULTIPLIER,
        status=status,
    )


def _build_record_count_metric(
    df: pl.DataFrame,
    baseline_stats: JsonDict,  # Any: heterogeneous baseline map
) -> StatisticalMetric | None:
    baseline_count = baseline_stats.get("record_count_ma30")
    if baseline_count is None:
        return None

    current_count = len(df)
    ratio = current_count / baseline_count if baseline_count > 0 else 1.0
    status = _record_count_status(ratio)
    return StatisticalMetric(
        current=float(current_count),
        baseline=float(baseline_count),
        ratio=round(ratio, 4),
        threshold_warning=RECORD_COUNT_WARNING_THRESHOLD,
        threshold_critical=RECORD_COUNT_CRITICAL_THRESHOLD,
        status=status,
    )


def _aggregate_profile_status(metrics: dict[str, StatisticalMetric]) -> DQCheckStatus:
    statuses = [metric.status for metric in metrics.values()]
    if any(status == DQCheckStatus.FAIL for status in statuses):
        return DQCheckStatus.FAIL
    if any(status == DQCheckStatus.WARN for status in statuses):
        return DQCheckStatus.WARN
    return DQCheckStatus.PASS


def check_statistical_profile(
    df: pl.DataFrame,
    baseline_stats: JsonDict  # Any: DQ check values vary by check type
    | None,  # Any: DQ baseline statistics have heterogeneous values
) -> StatisticalProfileResult:
    """Compare statistics against baseline (MA30).

    Args:
        df: Input DataFrame.
        baseline_stats: Baseline stats.

    Returns:
        Check result as StatisticalProfileResult.
    """
    if not baseline_stats:
        return StatisticalProfileResult(
            baseline_period_days=30,
            metrics={},
            status=DQCheckStatus.PASS,
        )

    metrics: dict[str, StatisticalMetric] = {}
    null_rate_metric = _build_null_rate_metric(df, baseline_stats)
    if null_rate_metric is not None:
        metrics["null_rate_avg"] = null_rate_metric

    record_count_metric = _build_record_count_metric(df, baseline_stats)
    if record_count_metric is not None:
        metrics["record_count_daily"] = record_count_metric

    return StatisticalProfileResult(
        baseline_period_days=30,
        metrics=metrics,
        status=_aggregate_profile_status(metrics),
    )


def check_anomaly_detection(
    df: pl.DataFrame,
    baseline_stats: JsonDict  # Any: DQ check values vary by check type
    | None,  # Any: DQ baseline statistics have heterogeneous values
) -> AnomalyDetectionResult:
    """Detect anomalies using baseline comparison.

    Args:
        df: Input DataFrame.
        baseline_stats: Baseline stats.

    Returns:
        Check result as AnomalyDetectionResult.
    """
    cold_start_days = 30
    current_day = baseline_stats.get("days_since_start", 0) if baseline_stats else 0
    cold_start_mode = current_day < cold_start_days

    if cold_start_mode or not baseline_stats:
        return AnomalyDetectionResult(
            cold_start_days=cold_start_days,
            current_day=current_day,
            cold_start_mode=True,
            anomalies_detected=(),
            metrics_monitored=(),
            status=DQCheckStatus.PASS,
        )

    anomalies: list[str] = []
    metrics_monitored: list[AnomalyMetric] = []

    # Null rate anomaly
    total_nulls = sum(df[col].null_count() for col in df.columns)
    total_cells = len(df) * len(df.columns)
    current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
    baseline_null_rate = baseline_stats.get("null_rate_ma30", current_null_rate)

    null_zscore = (
        (current_null_rate - baseline_null_rate) / baseline_null_rate
        if baseline_null_rate > 0
        else 0.0
    )

    if abs(null_zscore) > 3:
        anomalies.append("null_rate")
        null_status = "anomaly"
    else:
        null_status = "normal"

    metrics_monitored.append(
        AnomalyMetric(
            metric="null_rate",
            current_value=round(current_null_rate, 4),
            baseline_value=round(baseline_null_rate, 4),
            zscore=round(null_zscore, 2),
            status=null_status,
        )
    )

    # Record count anomaly
    current_count = float(len(df))
    baseline_count = baseline_stats.get("record_count_ma30", current_count)
    count_zscore = (
        (current_count - baseline_count) / baseline_count if baseline_count > 0 else 0.0
    )

    if abs(count_zscore) > 3:
        anomalies.append("record_count")
        count_status = "anomaly"
    else:
        count_status = "normal"

    metrics_monitored.append(
        AnomalyMetric(
            metric="record_count",
            current_value=current_count,
            baseline_value=baseline_count,
            zscore=round(count_zscore, 2),
            status=count_status,
        )
    )

    status = DQCheckStatus.WARN if anomalies else DQCheckStatus.PASS

    return AnomalyDetectionResult(
        cold_start_days=cold_start_days,
        current_day=current_day,
        cold_start_mode=False,
        anomalies_detected=tuple(anomalies),
        metrics_monitored=tuple(metrics_monitored),
        status=status,
    )
