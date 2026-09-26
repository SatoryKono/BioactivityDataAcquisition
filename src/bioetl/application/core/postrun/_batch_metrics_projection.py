"""Pure projection helpers for postrun batch metrics payloads."""

from __future__ import annotations

from bioetl.domain.ports import ExecutorMetricsPort


def project_batch_metrics(
    executor: ExecutorMetricsPort,
    *,
    freshness_anchor_timestamp: float,
) -> dict[str, float]:
    """Project executor counters into postrun metrics payload."""
    total_records = max(1, executor.records_fetched)
    return {
        "record_count": float(executor.records_fetched),
        "bronze_count": float(executor.records_bronze),
        "silver_count": float(executor.records_silver),
        "gold_count": float(executor.records_gold),
        "quarantined_count": float(executor.records_quarantined),
        "error_rate": executor.records_quarantined / total_records,
        "silver_yield": executor.records_silver / total_records,
        "gold_yield": executor.records_gold / total_records,
        "freshness_anchor_timestamp": freshness_anchor_timestamp,
    }
