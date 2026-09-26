"""Metric helpers for quarantine flows."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from bioetl.application.core.batch_metrics_accounting import (
    _record_silver_removal_accounting,
)
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.observability.pipeline_metrics import (
        PipelineMetricsRecorder,
    )
    from bioetl.domain.ports import MetricsPort

FILTERED_OUT_SILVER = "FILTERED_OUT_SILVER"


def iter_dq_quarantine_parts(
    records: Sequence[object],
):
    """Yield record, error type, message, and catalog reason code."""
    from bioetl.application.core.quarantine_manager import DQQuarantineEntry

    for item in records:
        if isinstance(item, DQQuarantineEntry):
            reason_code = item.reason_code or item.error_type.value
            yield item.record, item.error_type, item.error_details, reason_code
            continue
        record, error_type, error_details = item  # type: ignore[misc]
        yield record, error_type, error_details, error_type.value


def track_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    batch_metrics: BatchMetricsRecorderService | None,
    pipeline_name: str,
    run_type: str,
    error_type: ErrorType,
    count: int,
    stage: str = "silver",
    reason_code: str | None = None,
) -> None:
    """Emit quarantine metrics through batch, MetricsPort, and pipeline APIs.

    Pipeline accounting always runs. MetricsPort counters are best-effort when
    the port is injected; batch metrics take precedence when present.
    """
    if batch_metrics is not None:
        batch_metrics.track_quarantined_records(
            error_type, count, stage=stage, reason_code=reason_code
        )
        return
    elif metrics is not None:
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
    _record_silver_removal_accounting(
        outcome="quarantined",
        reason_code=reason_code or error_type.value,
        count=count,
        stage=stage,
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
    records: Sequence[object],
) -> Counter[ErrorType]:
    """Count DQ quarantine entries by error type."""
    return Counter(
        error_type for _, error_type, _, _ in iter_dq_quarantine_parts(records)
    )


def filtered_reason_code_from_details(
    details: object | None,
    *,
    fallback: str = FILTERED_OUT_SILVER,
) -> str:
    """Prefer ``details.reason_code`` for accounting; else the filter baseline."""
    if not isinstance(details, dict):
        return fallback
    raw = details.get("reason_code")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return fallback


def record_filtered_quarantine_metrics(
    *,
    metrics: MetricsPort | None,
    pipeline_metrics: PipelineMetricsRecorder,
    count: int,
    reason_code: str = FILTERED_OUT_SILVER,
    record_accounting: bool = True,
    emit_pipeline_metric: bool = True,
) -> None:
    """Emit metrics after a durable filter-rejection quarantine write.

    The durable write is the source of truth for filtered-out removals.
    ``reason_code`` should carry the per-entry catalog code when known.
    """
    _ = metrics
    if emit_pipeline_metric:
        pipeline_metrics.record_quarantine_records(
            reason=FILTERED_OUT_SILVER,
            count=count,
        )
    if record_accounting:
        _record_silver_removal_accounting(
            outcome="filtered_out",
            reason_code=reason_code or FILTERED_OUT_SILVER,
            count=count,
        )
