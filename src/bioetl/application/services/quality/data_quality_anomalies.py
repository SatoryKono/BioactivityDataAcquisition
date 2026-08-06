# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Metric and anomaly helpers for data-quality evaluation."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.value_objects.dq_anomaly import DQAnomaly
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort


class DataQualityMetricsMixin:
    """Freshness, DQ timing, and baseline metric helpers."""

    _dq_monitor: DQMonitorPort | None = cast(Any, None)  # Any: host default (PD4)
    _logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host default (PD4)
    _pipeline_name: str = cast(Any, None)  # Any: host default (PD4)
    _entity_type: str = cast(Any, None)  # Any: host default (PD4)
    _pipeline_metrics: PipelineMetricsRecorder = cast(
        Any, None
    )  # Any: host default (PD4)
    _run_type: str = cast(Any, None)  # Any: host default (PD4)

    @staticmethod
    def _resolve_freshness_anchor_timestamp(
        metrics: dict[str, float],
    ) -> float | None:
        """Resolve the canonical freshness anchor from evaluation metrics."""
        anchor = metrics.get("freshness_anchor_timestamp")
        if anchor is None or anchor <= 0:
            return None
        return anchor

    @staticmethod
    def _resolve_canonical_dq_timestamp(
        freshness_anchor_timestamp: float | None,
    ) -> datetime | None:
        """Translate the application freshness anchor into a UTC DQ timestamp."""
        if freshness_anchor_timestamp is None:
            return None
        return datetime.fromtimestamp(freshness_anchor_timestamp, UTC)

    def _record_check_duration(self, duration_ms: float) -> None:
        """Record DQ check duration metric."""
        if self._metrics:
            self._metrics.observe_histogram(
                "bioetl_dq_check_duration_ms",
                duration_ms,
                {"pipeline": self._pipeline_name},
            )

    def _update_baseline_metrics(
        self, metrics: dict[str, float], has_critical: bool
    ) -> None:
        """Update baseline metrics counters."""
        if not self._metrics or has_critical:
            return

        for metric_name in metrics:
            self._metrics.increment_counter(
                "bioetl_dq_baseline_updated",
                1,
                {"pipeline": self._pipeline_name, "metric": metric_name},
            )
            if self._dq_monitor is None:
                continue
            baseline_stats = self._dq_monitor.get_baseline_stats(metric_name)
            if (
                baseline_stats is None
                or not isinstance(baseline_stats, tuple)
                or len(baseline_stats) != 3
            ):
                continue
            _baseline_mean, _baseline_stddev, sample_count = baseline_stats
            self._metrics.set_gauge(
                "bioetl_dq_baseline_samples",
                float(sample_count),
                {"pipeline": self._pipeline_name, "metric": metric_name},
            )

    def _emit_dq_monitor_disabled_signal(self) -> None:
        """Emit an explicit signal when anomaly detection is unavailable."""
        self._logger.warning(
            "dq_monitor_disabled",
            pipeline=self._pipeline_name,
            entity=self._entity_type,
            reason="dq_monitor_not_configured",
        )
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_dq_monitor_disabled_total",
            1,
            {"pipeline": self._pipeline_name, "entity": self._entity_type},
        )

    def _emit_validation_stage_metrics(
        self,
        *,
        record_count: int,
    ) -> None:
        """Emit bounded validation-stage counts used for denominator semantics."""
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type,
            stage="validation",
            outcome="evaluated",
            count=record_count,
        )

    def _emit_validation_gauges(
        self,
        *,
        monitor_enabled: bool,
        error_rate: float,
        record_count: int,
        freshness_anchor: float | None,
    ) -> None:
        """Emit validation gauges for DQ dashboards and freshness alerts."""
        if self._metrics is None:
            return

        labels = {"pipeline": self._pipeline_name, "entity": self._entity_type}
        self._metrics.set_gauge(
            "bioetl_dq_monitor_enabled",
            1.0 if monitor_enabled else 0.0,
            labels,
        )
        self._metrics.set_gauge(
            "bioetl_dq_validation_score",
            1.0 - error_rate,
            labels,
        )
        self._metrics.set_gauge(
            "bioetl_dq_validation_record_count",
            record_count,
            labels,
        )
        if freshness_anchor is None:
            return

        # Dashboards and alerts derive lag via:
        #   time() - bioetl_data_freshness_seconds
        self._metrics.set_gauge(
            "bioetl_data_freshness_seconds",
            freshness_anchor,
            labels,
        )


class DataQualityAnomalyMixin(DataQualityMetricsMixin):
    """Anomaly detection and anomaly logging helpers."""

    _dq_monitor: DQMonitorPort | None = cast(Any, None)  # Any: host default (PD4)
    _logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host default (PD4)
    _pipeline_name: str = cast(Any, None)  # Any: host default (PD4)

    def _run_anomaly_detection(
        self,
        metrics: dict[str, float],
        error_rate: float,
        status: DQEvaluationStatus,
        canonical_dq_timestamp: datetime | None,
    ) -> DQResult:
        """Run anomaly detection, update baselines, and return results."""
        assert self._dq_monitor is not None
        if canonical_dq_timestamp is None:
            raise ValueError("canonical_dq_timestamp is required for anomaly detection")

        start_time = time.monotonic()
        anomalies = self._dq_monitor.check_quality(metrics, canonical_dq_timestamp)
        check_duration_ms = (time.monotonic() - start_time) * 1000

        self._record_check_duration(check_duration_ms)

        has_critical = self._process_anomalies(anomalies)

        self._dq_monitor.update_baseline_from_metrics(
            metrics,
            canonical_dq_timestamp,
        )
        self._update_baseline_metrics(metrics, has_critical)

        return DQResult(
            error_rate=error_rate,
            status=status,
            anomalies=tuple(anomalies),
            has_critical=has_critical,
            check_duration_ms=check_duration_ms,
        )

    def _process_anomalies(
        self,
        anomalies: list[DQAnomaly],
    ) -> bool:
        """Process detected anomalies and check for critical ones."""
        has_critical = False
        for anomaly in anomalies:
            self._process_single_anomaly(anomaly)
            if anomaly.severity.value == "critical":
                has_critical = True
        return has_critical

    def _process_single_anomaly(
        self,
        anomaly: DQAnomaly,
    ) -> None:
        """Log and track a single anomaly."""
        self._logger.warning(
            "dq_anomaly_detected",
            anomaly_type=anomaly.anomaly_type.value,
            severity=anomaly.severity.value,
            metric=anomaly.metric_name,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
        )

        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_dq_anomaly_detected",
                1,
                {
                    "pipeline": self._pipeline_name,
                    "metric": anomaly.metric_name,
                    "severity": anomaly.severity.value,
                    "anomaly_type": anomaly.anomaly_type.value,
                },
            )

        if anomaly.severity.value == "critical":
            self._logger.error(
                "critical_dq_anomaly",
                metric=anomaly.metric_name,
                message=anomaly.message,
            )


__all__ = ["DataQualityAnomalyMixin", "DataQualityMetricsMixin"]
