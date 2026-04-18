"""Shared phase runtime helpers for ``PostrunService``."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeVar

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.postrun.compact_orchestrator import CompactionResult
    from bioetl.application.core.postrun.service import PostrunResult
    from bioetl.application.services.dq_report_service import DQReportResult
    from bioetl.application.services.medallion_types import VacuumResult
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.value_objects.dq_result import DQResult

PostrunPhaseName = Literal[
    "compaction",
    "dq_evaluation",
    "dq_reports",
    "vacuum",
    "final_metadata",
]
PostrunLogLevel = Literal["info", "warning", "error"]
_ResultT = TypeVar("_ResultT")


@dataclass(frozen=True, slots=True)
class PostrunPhaseCompletion:
    """Phase success metadata for tracing and bounded observability."""

    status: str
    span_attributes: dict[str, object]
    observability_fields: dict[str, object]
    level: PostrunLogLevel | None = None


def resolve_postrun_phase_log_level(status: str) -> PostrunLogLevel:
    """Map bounded postrun status values to structured log levels."""
    if status == "failed":
        return "error"
    if status == "warning":
        return "warning"
    return "info"


def emit_postrun_phase_observability(
    *,
    metrics: MetricsPort,
    logger: LoggerPort,
    pipeline_name: str,
    phase_events_metric: str,
    phase_duration_metric: str,
    phase: PostrunPhaseName,
    status: str,
    duration_seconds: float,
    level: PostrunLogLevel | None = None,
    **extra: object,
) -> None:
    """Emit bounded metrics and structured logs for one postrun subphase."""
    labels = {
        "pipeline": pipeline_name,
        "phase": phase,
        "status": status,
    }
    metrics.increment_counter(
        phase_events_metric,
        1,
        labels=labels,
    )
    metrics.observe_histogram(
        phase_duration_metric,
        duration_seconds,
        labels=labels,
    )

    resolved_level = level or resolve_postrun_phase_log_level(status)
    log_payload: dict[str, object] = {
        "phase": phase,
        "status": status,
        "duration_seconds": round(duration_seconds, 4),
        **extra,
    }
    if resolved_level == "error":
        logger.error("postrun_phase_completed", **log_payload)
    elif resolved_level == "warning":
        logger.warning("postrun_phase_completed", **log_payload)
    else:
        logger.info("postrun_phase_completed", **log_payload)


def record_run_span_attributes(span: Span, result: PostrunResult) -> None:
    """Attach postrun outcome attributes to the active tracing span."""
    span.set_attribute("bioetl.dq_status", result.dq.status.value)
    span.set_attribute("bioetl.dq_anomalies_count", result.dq.anomalies_count)
    span.set_attribute("bioetl.dq_has_critical", result.dq.has_critical)
    span.set_attribute("bioetl.dq_check_duration_ms", result.dq.check_duration_ms)
    span.set_attribute(
        "bioetl.dq_reports_generated",
        bool(result.dq_reports and result.dq_reports.any_generated),
    )
    span.set_attribute(
        "bioetl.dq_reports_count",
        0 if result.dq_reports is None else result.dq_reports.reports_count,
    )
    span.set_attribute("bioetl.compaction_status", result.compaction.status)
    span.set_attribute(
        "bioetl.compaction_duplicates_removed",
        result.compaction.duplicates_removed,
    )
    span.set_attribute("bioetl.vacuum_skipped", result.vacuum.skipped)
    span.set_attribute(
        "bioetl.vacuum_silver_files_removed",
        result.vacuum.silver_files_removed,
    )
    span.set_attribute(
        "bioetl.vacuum_gold_files_removed",
        result.vacuum.gold_files_removed,
    )


async def run_async_postrun_phase(
    *,
    span_factory: Callable[[str], AbstractContextManager[Span]],
    phase: PostrunPhaseName,
    operation: Callable[[], Awaitable[_ResultT]],
    operation_errors: tuple[type[BaseException], ...],
    emit_phase_observability: Callable[..., None],
    on_success: Callable[[_ResultT], PostrunPhaseCompletion],
) -> _ResultT:
    """Run one async postrun phase with consistent tracing and failure handling."""
    start_time = time.perf_counter()
    with span_factory(f"postrun.{phase}") as span:
        try:
            result = await operation()
        except operation_errors as exc:
            emit_phase_observability(
                phase=phase,
                status="failed",
                duration_seconds=time.perf_counter() - start_time,
                level="error",
                error_type=type(exc).__name__,
            )
            raise
        completion = on_success(result)
        for key, value in completion.span_attributes.items():
            span.set_attribute(key, value)
        emit_phase_observability(
            phase=phase,
            status=completion.status,
            duration_seconds=time.perf_counter() - start_time,
            level=completion.level,
            **completion.observability_fields,
        )
        return result


def run_sync_postrun_phase(
    *,
    span_factory: Callable[[str], AbstractContextManager[Span]],
    phase: PostrunPhaseName,
    operation: Callable[[], _ResultT],
    operation_errors: tuple[type[BaseException], ...],
    emit_phase_observability: Callable[..., None],
    on_success: Callable[[_ResultT], PostrunPhaseCompletion],
) -> _ResultT:
    """Run one sync postrun phase with consistent tracing and failure handling."""
    start_time = time.perf_counter()
    with span_factory(f"postrun.{phase}") as span:
        try:
            result = operation()
        except operation_errors as exc:
            emit_phase_observability(
                phase=phase,
                status="failed",
                duration_seconds=time.perf_counter() - start_time,
                level="error",
                error_type=type(exc).__name__,
            )
            raise
        completion = on_success(result)
        for key, value in completion.span_attributes.items():
            span.set_attribute(key, value)
        emit_phase_observability(
            phase=phase,
            status=completion.status,
            duration_seconds=time.perf_counter() - start_time,
            level=completion.level,
            **completion.observability_fields,
        )
        return result


def describe_dq_phase(result: DQResult) -> PostrunPhaseCompletion:
    """Build tracing/logging metadata for the DQ phase."""
    return PostrunPhaseCompletion(
        status=result.status.value,
        span_attributes={
            "bioetl.dq_status": result.status.value,
            "bioetl.dq_anomalies_count": result.anomalies_count,
            "bioetl.dq_has_critical": result.has_critical,
            "bioetl.dq_check_duration_ms": result.check_duration_ms,
        },
        observability_fields={
            "anomalies_count": result.anomalies_count,
            "has_critical": result.has_critical,
            "check_duration_ms": result.check_duration_ms,
        },
    )


def describe_compaction_phase(result: CompactionResult) -> PostrunPhaseCompletion:
    """Build tracing/logging metadata for the compaction phase."""
    span_attributes: dict[str, object] = {
        "bioetl.compaction_status": result.status,
        "bioetl.compaction_duplicates_removed": result.duplicates_removed,
    }
    if result.error is not None:
        span_attributes["bioetl.compaction_error"] = result.error
    return PostrunPhaseCompletion(
        status=result.status,
        span_attributes=span_attributes,
        observability_fields={
            "duplicates_removed": result.duplicates_removed,
            "has_error": result.error is not None,
        },
        level="warning" if result.status == "failed" else None,
    )


def describe_dq_report_phase(
    result: DQReportResult | None,
) -> PostrunPhaseCompletion:
    """Build tracing/logging metadata for the DQ report phase."""
    return PostrunPhaseCompletion(
        status="generated" if result and result.any_generated else "skipped",
        span_attributes={
            "bioetl.dq_reports_generated": bool(result and result.any_generated),
            "bioetl.dq_reports_count": 0 if result is None else result.reports_count,
        },
        observability_fields={
            "reports_generated": bool(result and result.any_generated),
            "reports_count": 0 if result is None else result.reports_count,
        },
    )


def describe_vacuum_phase(result: VacuumResult) -> PostrunPhaseCompletion:
    """Build tracing/logging metadata for the VACUUM phase."""
    return PostrunPhaseCompletion(
        status="skipped" if result.skipped else "success",
        span_attributes={
            "bioetl.vacuum_skipped": result.skipped,
            "bioetl.vacuum_silver_files_removed": result.silver_files_removed,
            "bioetl.vacuum_gold_files_removed": result.gold_files_removed,
        },
        observability_fields={
            "silver_files_removed": result.silver_files_removed,
            "gold_files_removed": result.gold_files_removed,
            "skipped": result.skipped,
        },
    )


def describe_final_metadata_phase(
    *,
    wrote_metadata: bool,
    dq_reports: DQReportResult | None,
) -> PostrunPhaseCompletion:
    """Build tracing/logging metadata for the final-metadata phase."""
    return PostrunPhaseCompletion(
        status="success" if wrote_metadata else "skipped",
        span_attributes={
            "bioetl.final_metadata_phase_completed": True,
            "bioetl.dq_reports_available": dq_reports is not None,
        },
        observability_fields={
            "dq_reports_available": dq_reports is not None,
            "metadata_written": wrote_metadata,
        },
    )
