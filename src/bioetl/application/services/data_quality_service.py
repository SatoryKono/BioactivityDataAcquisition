"""Data Quality Service for centralized DQ evaluation.

Application Service that handles all data quality checks and anomaly detection.
Extracted from PostrunService to follow Single Responsibility Principle.

Responsibilities:
- Threshold checks (soft/hard fail)
- AnomalyRecord detection via DQMonitorPort
- DQ metrics emission
- Baseline updates

Does NOT handle:
- VACUUM operations (MedallionLifecycleService)
- Tracer cleanup (PostrunService)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_anomaly import DQAnomaly
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort


class _DataQualityThresholdMixin:
    """Threshold policy helpers for DQ evaluation."""

    _config: DQConfig
    _logger: LoggerPort
    _metrics: MetricsPort | None
    _pipeline_name: str
    _pipeline_metrics: PipelineMetricsRecorder
    _run_type: str

    def _emit_quarantine_semantics(
        self,
        *,
        quarantined_count: int,
        terminal_status: str,
    ) -> None:
        """Emit bounded quarantine semantics when validation isolated records."""
        if quarantined_count <= 0:
            return
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type,
            stage="validation",
            outcome="quarantined",
            count=quarantined_count,
        )
        self._pipeline_metrics.record_record_flow(
            run_type=self._run_type,
            flow_stage="quarantined",
            count=quarantined_count,
        )
        self._pipeline_metrics.record_dq_disposition(
            stage="validation",
            disposition="quarantine",
            terminal_status=terminal_status,
            count=quarantined_count,
        )

    def _check_hard_threshold(
        self, error_rate: float, quarantined_count: int = 0
    ) -> None:
        """Check if error rate exceeds hard threshold."""
        if self._config.hard_fail_threshold > 1.0:
            return
        if error_rate >= self._config.hard_fail_threshold:
            self._logger.error(
                "DQ hard threshold exceeded",
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
                pipeline=self._pipeline_name,
            )
            self._emit_quarantine_semantics(
                quarantined_count=quarantined_count,
                terminal_status="failed",
            )
            self._pipeline_metrics.record_dq_validation_failures(
                stage="threshold",
                severity="hard_fail",
            )
            self._pipeline_metrics.record_dq_disposition(
                stage="validation",
                disposition="fail",
                terminal_status="failed",
            )
            raise DataQualityThresholdError(
                error_rate=error_rate,
                threshold=self._config.hard_fail_threshold,
            )

    def _determine_status(self, error_rate: float) -> DQEvaluationStatus:
        """Determine DQ status based on error rate."""
        if error_rate >= self._config.soft_fail_threshold:
            return DQEvaluationStatus.WARNING
        return DQEvaluationStatus.PASSED

    def _emit_soft_threshold_warning(self, error_rate: float) -> None:
        """Log warning and emit metric for soft threshold breach."""
        self._logger.warning(
            "DQ soft threshold exceeded",
            error_rate=error_rate,
            threshold=self._config.soft_fail_threshold,
            pipeline=self._pipeline_name,
        )
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_dq_soft_threshold_exceeded",
                1,
                {"pipeline": self._pipeline_name},
            )
        self._pipeline_metrics.record_dq_validation_failures(
            stage="threshold",
            severity="soft_fail",
        )


class _DataQualityMetricsMixin:
    """Freshness, DQ timing, and baseline metric helpers."""

    _dq_monitor: DQMonitorPort | None
    _logger: LoggerPort
    _metrics: MetricsPort | None
    _pipeline_name: str
    _entity_type: str
    _pipeline_metrics: PipelineMetricsRecorder
    _run_type: str

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


class _DataQualityAnomalyMixin(_DataQualityMetricsMixin):
    """Anomaly detection and anomaly logging helpers."""

    _dq_monitor: DQMonitorPort | None
    _logger: LoggerPort
    _metrics: MetricsPort | None
    _pipeline_name: str

    def _run_anomaly_detection(
        self,
        metrics: dict[str, float],
        error_rate: float,
        status: DQEvaluationStatus,
        canonical_dq_timestamp: datetime | None,
    ) -> DQResult:
        """Run anomaly detection, update baselines, and return results."""
        assert self._dq_monitor is not None

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


class DataQualityService(
    _DataQualityThresholdMixin,
    _DataQualityAnomalyMixin,
):
    """Centralized service for data quality evaluation."""

    def __init__(
        self,
        dq_monitor: DQMonitorPort | None,
        config: DQConfig,
        logger: LoggerPort,
        metrics: MetricsPort | None,
        pipeline_name: str,
        entity_type: str,
        run_type: str = "unknown",
        pipeline_metrics: PipelineMetricsRecorder | None = None,
    ) -> None:
        """Initialize DataQualityService.

        Args:
            dq_monitor: Optional DQ monitor for anomaly detection.
            config: DQ configuration with soft/hard thresholds.
            logger: Structured logger for DQ events.
            metrics: Optional metrics port for observability.
            pipeline_name: Pipeline name for metric labels.
            entity_type: Entity type for metric labels.
            pipeline_metrics: Optional prebuilt pipeline-scoped metrics recorder.
        """
        self._dq_monitor = dq_monitor
        self._config = config
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name
        self._entity_type = entity_type
        self._run_type = run_type
        resolved_pipeline_metrics = pipeline_metrics
        if resolved_pipeline_metrics is None:
            resolved_pipeline_metrics = PipelineMetricsRecorder(
                metrics,
                pipeline_name,
            )
        self._pipeline_metrics = resolved_pipeline_metrics

    def evaluate(
        self,
        metrics: dict[str, float],
    ) -> DQResult:
        """Evaluate data quality based on metrics.

        Performs threshold checks before anomaly detection:
        1. If error_rate >= hard_fail_threshold: raises DataQualityThresholdError
        2. If error_rate >= soft_fail_threshold: logs warning + emits metric
        3. Then runs anomaly detection if dq_monitor is available

        Args:
            metrics: Dictionary of metric names to values.
                     Must contain 'error_rate' key.

        Returns:
            DQResult with evaluation outcome.

        Raises:
            DataQualityThresholdError: If error rate exceeds hard threshold.
        """
        error_rate = metrics.get("error_rate", 0.0)
        freshness_anchor = self._resolve_freshness_anchor_timestamp(metrics)
        canonical_dq_timestamp = self._resolve_canonical_dq_timestamp(freshness_anchor)
        record_count = max(int(metrics.get("record_count", 0.0)), 0)
        quarantined_count = max(int(metrics.get("quarantined_count", 0.0)), 0)

        # Emit validation score gauge (1.0 - error_rate)
        if self._metrics:
            labels = {"pipeline": self._pipeline_name, "entity": self._entity_type}
            self._metrics.set_gauge(
                "bioetl_dq_monitor_enabled",
                1.0 if self._dq_monitor is not None else 0.0,
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
            if freshness_anchor is not None:
                # Store the canonical ingestion/publication anchor timestamp in
                # seconds. Dashboards and alerts derive lag via:
                #   time() - bioetl_data_freshness_seconds
                self._metrics.set_gauge(
                    "bioetl_data_freshness_seconds",
                    freshness_anchor,
                    labels,
                )
        self._emit_validation_stage_metrics(
            record_count=record_count,
        )

        # Check hard threshold first - raises if exceeded
        self._check_hard_threshold(error_rate, quarantined_count)

        # Determine status based on soft threshold
        status = self._determine_status(error_rate)
        self._emit_quarantine_semantics(
            quarantined_count=quarantined_count,
            terminal_status="success",
        )

        # Log warning and emit metric if soft threshold exceeded
        if status == DQEvaluationStatus.WARNING:
            self._emit_soft_threshold_warning(error_rate)
            self._pipeline_metrics.record_dq_disposition(
                stage="validation",
                disposition="warn",
                terminal_status="success",
            )
        else:
            self._pipeline_metrics.record_dq_disposition(
                stage="validation",
                disposition="pass",
                terminal_status="success",
            )

        # Run anomaly detection if monitor available
        if self._dq_monitor is None:
            self._emit_dq_monitor_disabled_signal()
            return DQResult(
                error_rate=error_rate,
                status=status,
                anomalies=(),
                has_critical=False,
                check_duration_ms=0.0,
            )

        return self._run_anomaly_detection(
            metrics,
            error_rate,
            status,
            canonical_dq_timestamp,
        )


__all__ = ["DataQualityService"]
