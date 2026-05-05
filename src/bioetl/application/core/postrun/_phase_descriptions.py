"""Phase description helpers for PostrunService runtime phases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.postrun.compact_orchestrator import CompactionResult
    from bioetl.application.services.dq_report_service import DQReportResult
    from bioetl.application.services.medallion_types import VacuumResult
    from bioetl.domain.value_objects.dq_result import DQResult


class _PostrunResultProtocol(Protocol):
    dq: DQResult
    dq_reports: DQReportResult | None
    vacuum: VacuumResult
    compaction: CompactionResult

PostrunLogLevel = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class PostrunPhaseCompletion:
    """Success metadata for one postrun phase."""

    status: str
    span_attributes: dict[str, object]
    observability_fields: dict[str, object]
    level: PostrunLogLevel | None = None


def record_run_span_attributes(
    span: Span,
    result: _PostrunResultProtocol,
) -> None:
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


def describe_dq_phase(result: DQResult) -> PostrunPhaseCompletion:
    """Describe tracing and logging metadata for the DQ phase."""
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
    """Describe tracing and logging metadata for the compaction phase."""
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
    """Describe tracing and logging metadata for the DQ report phase."""
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
    """Describe tracing and logging metadata for the VACUUM phase."""
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
    """Describe tracing and logging metadata for the final-metadata phase."""
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
