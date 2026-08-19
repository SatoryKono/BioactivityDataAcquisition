"""Shared stage-metrics helpers for batch processing support choreography."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import TransformResult

__all__ = [
    "track_bronze_write_metrics",
    "track_storage_write_metrics",
    "track_transform_result_metrics",
]


def track_bronze_write_metrics(
    batch_metrics: BatchMetricsRecorderService,
    *,
    record_count: int,
) -> None:
    """Record Bronze-stage metrics after one batch write."""
    batch_metrics.track_batch_size("bronze", record_count)
    batch_metrics.track_processed_records("bronze", record_count)
    batch_metrics.track_batch_written(stage="bronze", count=record_count)
    batch_metrics.track_stage_records(
        stage="ingestion",
        outcome="bronze_written",
        count=record_count,
    )
    batch_metrics.track_stage_records(
        stage="bronze",
        outcome="records",
        count=record_count,
    )


def track_transform_result_metrics(
    batch_metrics: BatchMetricsRecorderService,
    *,
    transform_result: TransformResult,
) -> None:
    """Record transform-stage metrics derived from one TransformResult."""
    batch_metrics.track_processed_records(
        "silver", len(transform_result.silver_records)
    )
    batch_metrics.track_processed_records("gold", len(transform_result.gold_records))
    batch_metrics.track_stage_records(
        stage="transform",
        outcome="silver_ready",
        count=len(transform_result.silver_records),
    )
    batch_metrics.track_stage_records(
        stage="silver",
        outcome="valid",
        count=len(transform_result.silver_records),
    )
    batch_metrics.track_stage_records(
        stage="transform",
        outcome="gold_ready",
        count=len(transform_result.gold_records),
    )
    batch_metrics.track_stage_records(
        stage="gold",
        outcome="excluded_by_contract",
        count=transform_result.gold_excluded_by_contract_count,
    )


def track_storage_write_metrics(
    batch_metrics: BatchMetricsRecorderService,
    *,
    transform_result: TransformResult,
    silver_written: int | None = None,
    gold_written: int | None = None,
) -> None:
    """Record Silver/Gold storage-stage metrics after writes complete."""
    silver_count = (
        silver_written
        if silver_written is not None
        else len(transform_result.silver_records)
    )
    gold_count = (
        gold_written if gold_written is not None else len(transform_result.gold_records)
    )
    batch_metrics.track_stage_records(
        stage="storage",
        outcome="silver_written",
        count=silver_count,
    )
    batch_metrics.track_stage_records(
        stage="storage",
        outcome="gold_written",
        count=gold_count,
    )
    batch_metrics.track_stage_records(
        stage="gold",
        outcome="written",
        count=gold_count,
    )
