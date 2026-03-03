"""Batch metrics recording helper.

Encapsulates the logic for recording metrics during batch processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.types import ErrorType


class BatchMetricsRecorderService:
    """Helper to record metrics for a batch processing cycle.

    Encapsulates all metrics recording logic for batch ETL operations,
    providing a consistent interface for tracking:
    - Batch sizes at each processing stage
    - Record counts per stage
    - Error occurrences by type
    - Quarantined record counts

    All methods are safe to call with metrics=None (no-op).

    Attributes:
        _metrics: Metrics port instance (may be None).
        _pipeline_label: Label identifying the pipeline.
        _run_type_label: Label for the run type.

    """

    def __init__(
        self,
        metrics: MetricsPort | None,
        pipeline_label: str,
        run_type_label: str,
    ) -> None:
        """Initialize batch metrics recorder.

        Args:
            metrics: Metrics port instance.
            pipeline_label: Label identifying the pipeline (e.g., 'chembl_activity').
            run_type_label: Label for the run type (e.g., 'incremental', 'rebuild').

        """
        self._metrics = metrics
        self._pipeline_label = pipeline_label
        self._run_type_label = run_type_label

    def track_batch_size(self, stage: str, size: int) -> None:
        """Record the size of a batch at a specific stage.

        Records a histogram observation for batch_size_records metric.

        Args:
            stage: Processing stage name (e.g., 'bronze', 'silver', 'gold').
            size: Number of records in the batch.

        """
        if self._metrics:
            self._metrics.observe_histogram(
                "batch_size_records",
                size,
                {"pipeline": self._pipeline_label, "stage": stage},
            )

    def track_processed_records(self, stage: str, count: int) -> None:
        """Record number of processed records at a specific stage.

        Increments the records_processed_total counter with pipeline,
        stage, and run_type labels.

        Args:
            stage: Processing stage name (e.g., 'bronze', 'silver', 'gold', 'quarantined').
            count: Number of records processed.

        """
        if self._metrics:
            self._metrics.increment_counter(
                "records_processed_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "run_type": self._run_type_label,
                },
            )

    def track_error(self, stage: str, error_type: ErrorType) -> None:
        """Record an error occurrence at a specific stage.

        Increments the errors_total counter with pipeline, stage,
        and error_code labels.

        Args:
            stage: Processing stage where error occurred (e.g., 'transform', 'write').
            error_type: Classification of the error.

        """
        if self._metrics:
            self._metrics.increment_counter(
                "errors_total",
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
        """Record DQ validation failure with bounded labels.

        Args:
            stage: Validation stage label.
            severity: Failure severity (e.g. soft_fail, hard_fail).
            count: Number of failures.
        """
        if self._metrics:
            self._metrics.inc_dq_validation_failures(
                pipeline=self._pipeline_label,
                stage=stage,
                severity=severity,
                count=count,
            )

    def track_quarantined_records(self, error_type: ErrorType, count: int) -> None:
        """Record number of quarantined records.

        Args:
            error_type: Type of error that caused quarantine
            count: Number of records quarantined

        """
        if self._metrics:
            self._metrics.increment_counter(
                "dq_records_quarantined_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "error_type": error_type.value,
                    "run_type": self._run_type_label,
                },
            )
            self._metrics.inc_quarantine_records(
                pipeline=self._pipeline_label,
                reason=error_type.value,
                count=count,
            )


BatchMetricsRecorder = BatchMetricsRecorderService

__all__ = ["BatchMetricsRecorder", "BatchMetricsRecorderService"]
