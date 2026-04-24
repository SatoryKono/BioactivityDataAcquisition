"""Postrun emission helpers for the pipeline observer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.events import PipelineEvent

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


class _ObserverPostrunEmissionMixin:
    """Postrun anomaly and maintenance emission helpers."""

    pipeline_name: str
    _metrics: MetricsPort

    def emit_dq_anomaly(
        self,
        metric_name: str,
        severity: str,
        anomaly_type: str,
        current_value: float,
        baseline_mean: float | None = None,
        **extra: Any,  # Any: anomaly events propagate arbitrary postrun context fields to the observer bus.
    ) -> None:
        """Emit data quality anomaly detection event."""
        level = "error" if severity == "critical" else "warning"
        self.emit_event(
            PipelineEvent.DQ_ANOMALY_DETECTED,
            self.LifecyclePhase.POSTRUN,
            level=level,
            metric=metric_name,
            dq_severity=severity,
            anomaly_type=anomaly_type,
            current_value=current_value,
            baseline_mean=baseline_mean,
            **extra,
        )

        self._metrics.increment_counter(
            "bioetl_dq_anomaly_detected",
            1,
            {
                "pipeline": self.pipeline_name,
                "metric": metric_name,
                "severity": severity,
                "anomaly_type": anomaly_type,
            },
        )

    def emit_vacuum_result(
        self,
        layer: str,
        table: str,
        files_removed: int,
        success: bool = True,
        **extra: Any,  # Any: maintenance events expose optional provider-specific payload fields.
    ) -> None:
        """Emit VACUUM operation result."""
        self.emit_event(
            PipelineEvent.VACUUM_COMPLETED,
            self.LifecyclePhase.POSTRUN,
            level="info" if success else "warning",
            layer=layer,
            table=table,
            files_removed=files_removed,
            success=success,
            **extra,
        )

        if success:
            self._metrics.increment_counter(
                "bioetl_vacuum_files_removed_total",
                files_removed,
                {"table": table, "layer": layer},
            )
