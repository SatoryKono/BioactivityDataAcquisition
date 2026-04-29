"""Application-level helpers for pipeline-specific metrics semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


@dataclass(slots=True)
class _PipelineMetricsRecorderCore:
    """Wrap generic metric dispatch with BioETL pipeline-level semantics.

    This facade lives in the application layer so ``MetricsPort`` can remain a
    transport-oriented contract while runtime-specific metric vocabulary stays
    outside the generic domain port.
    """

    metrics: MetricsPort | None
    pipeline: str

    def record_quarantine_records(
        self,
        *,
        reason: str,
        count: int = 1,
    ) -> None:
        """Increment the bounded quarantine record counter."""
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_quarantine_records_total",
            count,
            {"pipeline": self.pipeline, "reason": reason},
        )

    def record_dq_validation_failures(
        self,
        *,
        stage: str,
        severity: str,
        count: int = 1,
    ) -> None:
        """Increment bounded DQ validation failure counters."""
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_dq_validation_failures_total",
            count,
            {
                "pipeline": self.pipeline,
                "stage": stage,
                "severity": severity,
            },
        )

    def record_silver_filter_rejections(
        self,
        *,
        run_type: str,
        reason_code: str | None = None,
        rule_type: str | None = None,
        field: str | None = None,
        count: int = 1,
    ) -> None:
        """Increment bounded Silver filter rejection counters."""
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_silver_filter_rejections_total",
            count,
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "reason_code": reason_code or "",
                "rule_type": rule_type or "",
                "field": field or "",
            },
        )

    def record_record_flow(
        self,
        *,
        run_type: str,
        flow_stage: str,
        count: int = 1,
    ) -> None:
        """Increment the canonical bounded record-flow projection counter."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_record_flow_records_total",
            count,
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "flow_stage": flow_stage,
            },
        )

    def record_stage_records(
        self,
        *,
        run_type: str,
        stage: str,
        outcome: str,
        count: int = 1,
    ) -> None:
        """Increment the canonical stage-model projection counter."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_stage_records_total",
            count,
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "stage": stage,
                "outcome": outcome,
            },
        )

    def record_flow_invariant(
        self,
        *,
        run_type: str,
        invariant: str,
        status: str,
        count: int = 1,
    ) -> None:
        """Increment bounded terminal invariant outcomes for record-flow accounting."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_record_flow_invariants_total",
            count,
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "invariant": invariant,
                "status": status,
            },
        )

    def record_stage_backlog(
        self,
        *,
        run_type: str,
        stage: str,
        count: int,
    ) -> None:
        """Set the bounded unresolved backlog gauge for one canonical stage."""
        if self.metrics is None or count < 0:
            return
        self.metrics.set_gauge(
            "bioetl_stage_backlog_records",
            float(count),
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "stage": stage,
            },
        )

    def record_stage_lag_seconds(
        self,
        *,
        run_type: str,
        stage: str,
        seconds: float,
    ) -> None:
        """Set the bounded unresolved stage lag gauge for one canonical stage."""
        if self.metrics is None or seconds < 0:
            return
        self.metrics.set_gauge(
            "bioetl_stage_lag_seconds",
            seconds,
            {
                "pipeline": self.pipeline,
                "run_type": run_type,
                "stage": stage,
            },
        )

    def record_dq_disposition(
        self,
        *,
        stage: str,
        disposition: str,
        terminal_status: str,
        count: int = 1,
    ) -> None:
        """Increment bounded DQ disposition events with terminal correlation."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_dq_dispositions_total",
            count,
            {
                "pipeline": self.pipeline,
                "stage": stage,
                "disposition": disposition,
                "terminal_status": terminal_status,
            },
        )

    def record_batch_lifecycle_event(
        self,
        *,
        run_type: str,
        event: str,
        stage: str,
        status: str,
        count: int = 1,
        record_count: int = 0,
    ) -> None:
        """Increment bounded batch lifecycle event and record counters."""
        if self.metrics is None or count <= 0:
            return
        labels = {
            "pipeline": self.pipeline,
            "run_type": run_type,
            "event": event,
            "stage": stage,
            "status": status,
        }
        self.metrics.increment_counter(
            "bioetl_batch_lifecycle_events_total",
            count,
            labels,
        )
        if record_count > 0:
            self.metrics.increment_counter(
                "bioetl_batch_lifecycle_records_total",
                record_count,
                labels,
            )

    def record_output_artifact_publication(
        self,
        *,
        stage: str,
        status: str,
        count: int = 1,
    ) -> None:
        """Increment bounded output artifact publication outcomes."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_output_artifact_publication_events_total",
            count,
            {
                "pipeline": self.pipeline,
                "stage": stage,
                "status": status,
            },
        )


class _CompositePhaseMetricsRecorderMixin:
    """Composite-phase specific metrics emitted by pipeline-scoped recorders."""

    def record_composite_phase_records(
        self,
        *,
        phase: str,
        outcome: str,
        count: int = 1,
    ) -> None:
        """Increment bounded composite phase record counters."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_composite_phase_records_total",
            count,
            {
                "pipeline": self.pipeline,
                "phase": phase,
                "outcome": outcome,
            },
        )

    def record_composite_phase_errors(
        self,
        *,
        phase: str,
        error_kind: str,
        count: int = 1,
    ) -> None:
        """Increment bounded composite phase error counters."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_composite_phase_errors_total",
            count,
            {
                "pipeline": self.pipeline,
                "phase": phase,
                "error_kind": error_kind,
            },
        )

    def record_composite_phase_loss(
        self,
        *,
        phase: str,
        loss_kind: str,
        count: int = 1,
    ) -> None:
        """Increment bounded composite phase loss counters."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_composite_phase_loss_total",
            count,
            {
                "pipeline": self.pipeline,
                "phase": phase,
                "loss_kind": loss_kind,
            },
        )

    def record_composite_phase_retries(
        self,
        *,
        phase: str,
        retry_kind: str,
        count: int = 1,
    ) -> None:
        """Increment bounded composite phase retry or resume counters."""
        if self.metrics is None or count <= 0:
            return
        self.metrics.increment_counter(
            "bioetl_composite_phase_retries_total",
            count,
            {
                "pipeline": self.pipeline,
                "phase": phase,
                "retry_kind": retry_kind,
            },
        )


class PipelineMetricsRecorder(
    _CompositePhaseMetricsRecorderMixin,
    _PipelineMetricsRecorderCore,
):
    """Public pipeline-scoped metrics facade used by runtime/application code."""
