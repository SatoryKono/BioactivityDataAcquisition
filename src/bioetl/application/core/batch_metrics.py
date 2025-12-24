"""Batch metrics recording helper.

Encapsulates the logic for recording metrics during batch processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.types import ErrorType


class BatchMetricsRecorder:
    """Helper to record metrics for a batch processing cycle."""

    def __init__(
        self,
        metrics: MetricsPort | None,
        pipeline_label: str,
        run_type_label: str,
    ):
        self._metrics = metrics
        self._pipeline_label = pipeline_label
        self._run_type_label = run_type_label

    def track_batch_size(self, stage: str, size: int) -> None:
        """Record the size of a batch at a specific stage."""
        if self._metrics:
            self._metrics.observe_histogram(
                "batch_size_records",
                size,
                {"pipeline": self._pipeline_label, "stage": stage},
            )

    def track_processed_records(self, stage: str, count: int) -> None:
        """Record number of processed records at a specific stage."""
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
        """Record an error occurrence."""
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

    def track_dq_quarantined(
        self, count: int, error_type: str = "data_quality"
    ) -> None:
        """Record DQ quarantined records.

        Args:
            count: Number of records quarantined
            error_type: Type of DQ error (default: "data_quality")
        """
        if self._metrics:
            self._metrics.increment_counter(
                "dq_records_quarantined_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "error_type": error_type,
                    "run_type": self._run_type_label,
                },
            )
