"""Metric helpers for quarantine flows."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from bioetl.application.core.batch_metrics import _record_silver_removal_accounting
from bioetl.domain.types import BronzeRecord, ErrorType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.domain.ports import MetricsPort

FILTERED_OUT_SILVER = "FILTERED_OUT_SILVER"

def track_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    batch_metrics: BatchMetricsRecorderService | None,
    pipeline_name: str,
    run_type: str,
    error_type: ErrorType,
    count: int,
) -> None:
    """Emit quarantine metrics through both legacy and current metric APIs."""
    if batch_metrics is not None:
        batch_metrics.track_quarantined_records(error_type, count)
        return

    if metrics is None:
        return

    track_quarantined_records = getattr(metrics, "track_quarantined_records", None)
    if callable(track_quarantined_records):
        track_quarantined_records(error_type, count)

    metrics.increment_counter(
        "bioetl_dq_records_quarantined_total",
        count,
        {
            "pipeline": pipeline_name,
            "error_type": error_type.value,
            "run_type": run_type,
        },
    )
    pipeline_metrics.record_quarantine_records(
        reason=error_type.value,
        count=count,
    )

def track_processed_quarantined(
    *,
    metrics: MetricsPort | None,
    batch_metrics: BatchMetricsRecorderService | None,
    pipeline_name: str,
    run_type: str,
    count: int,
) -> None:
    """Emit processed-record metrics for the quarantine stage."""
    if batch_metrics is not None:
        batch_metrics.track_processed_records("quarantined", count)
        return

    if metrics is None:
        return

    track_processed_records = getattr(metrics, "track_processed_records", None)
    if callable(track_processed_records):
        track_processed_records("quarantined", count)

    metrics.increment_counter(
        "bioetl_records_processed_total",
        count,
        {
            "pipeline": pipeline_name,
            "stage": "quarantined",
            "run_type": run_type,
        },
    )

def count_dq_error_types(
    records: Sequence[tuple[BronzeRecord, ErrorType, str]],
) -> Counter[ErrorType]:
    """Count DQ quarantine entries by error type."""
    return Counter(error_type for _, error_type, _ in records)

def record_filtered_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    count: int,
) -> None:
    """Emit metrics for filter-rejected records."""
    if metrics is None:
        return
    pipeline_metrics.record_quarantine_records(
        reason=FILTERED_OUT_SILVER,
        count=count,
    )
    _record_silver_removal_accounting(
        outcome="filtered_out",
        reason_code=FILTERED_OUT_SILVER,
        count=count,
    )
