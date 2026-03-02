"""Statistical DQ checks: statistical profile, anomaly detection.

Extracted from GoldDQAnalyzer per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from bioetl.domain.value_objects.dq_report import (
    AnomalyDetectionResult,
    AnomalyMetric,
    DQCheckStatus,
    StatisticalMetric,
    StatisticalProfileResult,
)

# Thresholds from RULES.md §3.4.1
NULL_RATE_WARNING_MULTIPLIER = 2.0
NULL_RATE_CRITICAL_MULTIPLIER = 5.0
RECORD_COUNT_WARNING_THRESHOLD = 0.70
RECORD_COUNT_CRITICAL_THRESHOLD = 0.50


def check_statistical_profile(
    df: pl.DataFrame, baseline_stats: dict[str, Any] | None
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

    if "null_rate_ma30" in baseline_stats:
        total_nulls = sum(df[col].null_count() for col in df.columns)
        total_cells = len(df) * len(df.columns)
        current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
        baseline_null_rate = baseline_stats["null_rate_ma30"]

        ratio = (
            current_null_rate / baseline_null_rate if baseline_null_rate > 0 else 1.0
        )

        if ratio > NULL_RATE_CRITICAL_MULTIPLIER:
            status = DQCheckStatus.FAIL
        elif ratio > NULL_RATE_WARNING_MULTIPLIER:
            status = DQCheckStatus.WARN
        else:
            status = DQCheckStatus.PASS

        metrics["null_rate_avg"] = StatisticalMetric(
            current=round(current_null_rate, 4),
            baseline=round(baseline_null_rate, 4),
            ratio=round(ratio, 4),
            threshold_warning=NULL_RATE_WARNING_MULTIPLIER,
            threshold_critical=NULL_RATE_CRITICAL_MULTIPLIER,
            status=status,
        )

    if "record_count_ma30" in baseline_stats:
        current_count = len(df)
        baseline_count = baseline_stats["record_count_ma30"]

        ratio = current_count / baseline_count if baseline_count > 0 else 1.0

        if ratio < RECORD_COUNT_CRITICAL_THRESHOLD:
            status = DQCheckStatus.FAIL
        elif ratio < RECORD_COUNT_WARNING_THRESHOLD:
            status = DQCheckStatus.WARN
        else:
            status = DQCheckStatus.PASS

        metrics["record_count_daily"] = StatisticalMetric(
            current=float(current_count),
            baseline=float(baseline_count),
            ratio=round(ratio, 4),
            threshold_warning=RECORD_COUNT_WARNING_THRESHOLD,
            threshold_critical=RECORD_COUNT_CRITICAL_THRESHOLD,
            status=status,
        )

    overall_status = DQCheckStatus.PASS
    for metric in metrics.values():
        if metric.status == DQCheckStatus.FAIL:
            overall_status = DQCheckStatus.FAIL
            break
        elif metric.status == DQCheckStatus.WARN:
            overall_status = DQCheckStatus.WARN

    return StatisticalProfileResult(
        baseline_period_days=30,
        metrics=metrics,
        status=overall_status,
    )


def check_anomaly_detection(
    df: pl.DataFrame, baseline_stats: dict[str, Any] | None
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
