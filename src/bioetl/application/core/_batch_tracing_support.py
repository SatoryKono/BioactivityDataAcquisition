"""Private helpers for batch tracing attribute shaping."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BatchID, JsonDict

type SpanAttributeValue = (
    str
    | bool
    | int
    | float
    | tuple[str, ...]
    | tuple[bool, ...]
    | tuple[int, ...]
    | tuple[float, ...]
)


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


def set_memory_decision_trace_attributes(
    span: Span,
    *,
    memory_decision_trace: tuple[JsonDict, ...],
) -> None:
    """Set bounded adaptive-memory summary attributes on a span."""
    decision_count = len(memory_decision_trace)
    resize_count = sum(
        1
        for entry in memory_decision_trace
        if entry.get("old_batch_size") != entry.get("new_batch_size")
    )
    pressure_event_count = sum(
        1 for entry in memory_decision_trace if entry.get("pressure_state") is True
    )
    monitor_modes = sorted(
        {
            str(mode)
            for entry in memory_decision_trace
            if (mode := entry.get("monitor_mode")) is not None
        }
    )
    span.set_attribute("bioetl.memory_decision_count", decision_count)
    span.set_attribute("bioetl.memory_resize_event_count", resize_count)
    span.set_attribute("bioetl.memory_pressure_event_count", pressure_event_count)
    span.set_attribute(
        "bioetl.memory_monitor_modes",
        ",".join(monitor_modes) if monitor_modes else "none",
    )


def add_memory_decision_trace_events(
    span: Span,
    *,
    memory_decision_trace: tuple[JsonDict, ...],
) -> None:
    """Attach bounded adaptive-memory decisions as root-span events."""
    for entry in memory_decision_trace:
        attributes: dict[str, SpanAttributeValue] = {
            "bioetl.memory.decision_index": int(entry["decision_index"]),
            "bioetl.memory.stage": str(entry["stage"]),
            "bioetl.memory.old_batch_size": int(entry["old_batch_size"]),
            "bioetl.memory.new_batch_size": int(entry["new_batch_size"]),
            "bioetl.memory.reason": str(entry["reason"]),
            "bioetl.memory.monitor_mode": str(entry["monitor_mode"]),
            "bioetl.memory.adaptive_sizing_enabled": bool(
                entry["adaptive_sizing_enabled"]
            ),
            "bioetl.memory.monitor_available": bool(entry["monitor_available"]),
            "bioetl.memory.config_available": bool(entry["config_available"]),
        }
        if (record_index := entry.get("record_index")) is not None:
            attributes["bioetl.memory.record_index"] = int(record_index)
        if (pressure_state := entry.get("pressure_state")) is not None:
            attributes["bioetl.memory.pressure_state"] = bool(pressure_state)
        span.add_event("bioetl.memory.decision", attributes=attributes)


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
