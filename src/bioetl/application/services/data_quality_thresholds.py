# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Threshold and disposition helpers for data-quality evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus

if TYPE_CHECKING:
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import LoggerPort, MetricsPort


class DataQualityThresholdMixin:
    """Threshold policy helpers for DQ evaluation."""

    _config: DQConfig = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _pipeline_name: str = cast(Any, None)  # Any: host attr default (PD3)
    _pipeline_metrics: PipelineMetricsRecorder = cast(Any, None)  # Any: host attr default (PD3)
    _run_type: str = cast(Any, None)  # Any: host attr default (PD3)

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
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type,
            stage="silver",
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


__all__ = ["DataQualityThresholdMixin"]
