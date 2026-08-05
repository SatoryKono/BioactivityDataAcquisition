"""Data Quality Service for centralized DQ evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.services.quality.data_quality_anomalies import DataQualityAnomalyMixin
from bioetl.application.services.quality.data_quality_thresholds import (
    DataQualityThresholdMixin,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort


class DataQualityService(
    DataQualityThresholdMixin,
    DataQualityAnomalyMixin,
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
        """Initialize DataQualityService."""
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

        self._emit_validation_gauges(
            monitor_enabled=self._dq_monitor is not None,
            error_rate=error_rate,
            record_count=record_count,
            freshness_anchor=freshness_anchor,
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
