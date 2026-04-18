"""Private helpers for batch tracing attribute shaping."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BatchID


def build_execution_span_attributes(
    *,
    pipeline_name: str | None,
    entity_type: str,
    context: PipelineContext,
    adaptive_batch_sizing_enabled: bool,
    initial_batch_size: int,
) -> dict[str, str | bool | int]:
    """Build root execution span attributes."""
    return {
        "bioetl.pipeline": pipeline_name or "unknown",
        "bioetl.run_id": str(context.run_id),
        "bioetl.entity_type": entity_type,
        "bioetl.run_type": context.run_type.value,
        "bioetl.adaptive_batch_sizing": adaptive_batch_sizing_enabled,
        "bioetl.initial_batch_size": initial_batch_size,
    }


def build_batch_span_attributes(
    *,
    batch_id: BatchID,
    record_count: int,
    run_type: str,
    entity_type: str,
    start_index: int,
) -> dict[str, str | int]:
    """Build batch-level tracing attributes."""
    return {
        "bioetl.batch_id": str(batch_id),
        "bioetl.record_count": record_count,
        "bioetl.run_type": run_type,
        "bioetl.entity_type": entity_type,
        "bioetl.start_index": start_index,
    }


def build_layer_span_attributes(
    *,
    batch_id: BatchID,
    count: int,
    input_count: bool,
) -> dict[str, str | int]:
    """Build per-layer span attributes."""
    count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
    return {"bioetl.batch_id": str(batch_id), count_key: count}


def set_execution_stats_attributes(
    span: Span,
    *,
    total_fetched: int,
    total_bronze: int,
    total_silver: int,
    total_gold: int,
    total_quarantined: int,
    batch_size_reductions: int,
    min_batch_size_used: int,
) -> None:
    """Set final execution statistics on a span."""
    for key, value in (
        ("bioetl.total_fetched", total_fetched),
        ("bioetl.total_bronze", total_bronze),
        ("bioetl.total_silver", total_silver),
        ("bioetl.total_gold", total_gold),
        ("bioetl.total_quarantined", total_quarantined),
        ("bioetl.batch_size_reductions", batch_size_reductions),
        ("bioetl.min_batch_size_used", min_batch_size_used),
    ):
        span.set_attribute(key, value)


def set_record_result_attributes(
    span: Span,
    *,
    silver_count: int,
    gold_count: int,
    quarantined_count: int,
    bronze_count: int | None = None,
) -> None:
    """Set batch/transform count attributes on a span."""
    if bronze_count is not None:
        span.set_attribute("bioetl.bronze_count", bronze_count)
    span.set_attribute("bioetl.silver_count", silver_count)
    span.set_attribute("bioetl.gold_count", gold_count)
    span.set_attribute("bioetl.quarantined_count", quarantined_count)
