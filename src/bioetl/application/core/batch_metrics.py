"""Batch metrics recording helper.

Encapsulates the logic for recording metrics during batch processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.batch_metrics_accounting import (
    _FLOW_ACCOUNTING_STAGES,
    _GOLD_REMOVAL_REASONS,
    _SILVER_REMOVAL_REASONS,
    _record_filtered_out_stage_metrics,
    _record_processed_stage_accounting,
    _record_silver_removal_accounting,
    _record_stage_outcome_accounting,
    _silver_filter_rejection_labels,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.run_reports.context import get_stage_accounting
from bioetl.domain.run_reports.models import StageId

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.types import ErrorType, JsonDict


class BatchMetricsRecorderService:
    """Record bounded batch-processing metrics; all methods are metrics-safe no-ops."""

    def __init__(
        self,
        metrics: MetricsPort | None,
        pipeline_label: str,
        run_type_label: str,
        pipeline_metrics: PipelineMetricsRecorder | None = None,
    ) -> None:
        """Initialize pipeline-scoped batch metrics helpers."""
        self._metrics = metrics
        self._pipeline_label = pipeline_label
        self._run_type_label = run_type_label
        self._pipeline_metrics = (
            pipeline_metrics
            if pipeline_metrics is not None
            else PipelineMetricsRecorder(metrics, pipeline_label)
        )
        self._error_count = 0

    @property
    def error_count(self) -> int:
        """Get the current error count."""
        return self._error_count

    def track_batch_size(self, stage: str, size: int) -> None:
        """Record a batch-size histogram sample for one processing stage."""
        if self._metrics:
            self._metrics.observe_histogram(
                "bioetl_batch_size_records",
                size,
                {"pipeline": self._pipeline_label, "stage": stage},
            )

    def track_records_fetched(self, count: int) -> None:
        """Record the bounded fetched-side record-flow projection."""
        self._pipeline_metrics.record_record_flow(
            run_type=self._run_type_label,
            flow_stage="fetched",
            count=count,
        )
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type_label,
            stage="input",
            outcome="fetched",
            count=count,
        )
        accounting = get_stage_accounting()
        if accounting is not None and count > 0:
            accounting.record_in(StageId.EXTRACT.value, count)
            accounting.mark_instrumented(StageId.EXTRACT.value)

    def track_batch_created(self, *, stage: str, count: int) -> None:
        """Record one successful batch-created lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="created",
            stage=stage,
            status="success",
            count=1,
            record_count=count,
        )

    def track_batch_written(self, *, stage: str, count: int) -> None:
        """Record one successful batch-written lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="written",
            stage=stage,
            status="success",
            count=1,
            record_count=count,
        )

    def track_batch_failed(self, *, stage: str, count: int = 0) -> None:
        """Record one failed batch lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="failed",
            stage=stage,
            status="failed",
            count=1,
            record_count=count,
        )

    def track_processed_records(self, stage: str, count: int) -> None:
        """Record processed-record counters and canonical flow projections."""
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_records_processed_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "run_type": self._run_type_label,
                },
            )
        if stage in _FLOW_ACCOUNTING_STAGES:
            self._pipeline_metrics.record_record_flow(
                run_type=self._run_type_label,
                flow_stage=stage,
                count=count,
            )
        if stage == "filtered_out":
            _record_filtered_out_stage_metrics(
                self._pipeline_metrics,
                run_type_label=self._run_type_label,
                count=count,
            )
            return
        _record_processed_stage_accounting(stage, count)

    def track_error(self, stage: str, error_type: ErrorType) -> None:
        """Record one stage-scoped error occurrence."""
        self._error_count += 1
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_errors_total",
                1,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "error_code": error_type.value,
                },
            )

    def track_dq_validation_failure(
        self, stage: str, severity: str, count: int = 1
    ) -> None:
        """Record DQ validation failures with bounded stage/severity labels."""
        self._pipeline_metrics.record_dq_validation_failures(
            stage=stage,
            severity=severity,
            count=count,
        )

    def track_stage_records(
        self,
        *,
        stage: str,
        outcome: str,
        count: int,
    ) -> None:
        """Record one canonical stage-model outcome when the count is positive."""
        if count <= 0:
            return
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type_label,
            stage=stage,
            outcome=outcome,
            count=count,
        )
        _record_stage_outcome_accounting(stage, outcome, count)

    def track_quarantined_records(self, error_type: ErrorType, count: int) -> None:
        """Record quarantined-record counters and flow projections."""
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_dq_records_quarantined_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "error_type": error_type.value,
                    "run_type": self._run_type_label,
                },
            )
            self._pipeline_metrics.record_quarantine_records(
                reason=error_type.value,
                count=count,
            )
            self._pipeline_metrics.record_record_flow(
                run_type=self._run_type_label,
                flow_stage="quarantined",
                count=count,
            )
        _record_silver_removal_accounting(
            outcome="quarantined",
            reason_code=getattr(error_type, "value", str(error_type)),
            count=count,
        )

    def track_silver_filter_rejection(
        self,
        details: JsonDict | None = None,
        count: int = 1,
    ) -> None:
        """Record bounded Silver-filter reject breakdown labels.

        `message` remains display-only and is intentionally ignored here.
        """
        if not self._metrics:
            return
        reason_code, rule_type, field = _silver_filter_rejection_labels(details)
        self._pipeline_metrics.record_silver_filter_rejections(
            run_type=self._run_type_label,
            reason_code=reason_code,
            rule_type=rule_type,
            field=field,
            count=count,
        )
        _record_silver_removal_accounting(
            outcome="filtered_out",
            reason_code=reason_code or "FILTERED_OUT_SILVER",
            count=count,
        )


# Compatibility alias retained for legacy imports.
BatchMetricsRecorder = BatchMetricsRecorderService

__all__ = ["BatchMetricsRecorder", "BatchMetricsRecorderService"]
