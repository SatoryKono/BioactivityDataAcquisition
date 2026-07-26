"""Batch metrics recording helper.

Encapsulates the logic for recording metrics during batch processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.run_reports.context import get_stage_accounting
from bioetl.domain.run_reports.models import StageId

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.types import ErrorType, JsonDict

_FLOW_ACCOUNTING_STAGES = frozenset({"bronze", "silver", "gold", "filtered_out"})
_SILVER_REMOVAL_REASONS = {
    "filtered_out": "FILTERED_OUT_SILVER",
    "quarantined": "SCHEMA_VALIDATION_FAILURE",
    "skipped": "UNKNOWN_REASON",
    "deduplicated": "DEDUP_KEY_COLLISION",
}
_GOLD_REMOVAL_REASONS = {
    "excluded_by_contract": "gold_contract_schema_failure",
    "quarantined": "gold_semantic_business_exclusion",
    "skipped": "UNKNOWN_REASON",
    "deduplicated": "DEDUP_KEY_COLLISION",
}


def _record_silver_removal_accounting(
    *,
    outcome: str,
    reason_code: str,
    count: int,
) -> None:
    """Record one positive Silver-stage removal in run accounting."""
    accounting = get_stage_accounting()
    if accounting is None or count <= 0:
        return
    accounting.record_removal(
        StageId.SILVER.value,
        outcome=outcome,
        reason_code=reason_code,
        count=count,
    )


def _record_filtered_out_stage_metrics(
    pipeline_metrics: PipelineMetricsRecorder,
    *,
    run_type_label: str,
    count: int,
) -> None:
    """Project filtered-out counts into transform/silver stage metrics + accounting."""
    pipeline_metrics.record_stage_records(
        run_type=run_type_label,
        stage="transform",
        outcome="filtered_out",
        count=count,
    )
    pipeline_metrics.record_stage_records(
        run_type=run_type_label,
        stage="silver",
        outcome="filtered_out",
        count=count,
    )
    _record_silver_removal_accounting(
        outcome="filtered_out",
        reason_code="FILTERED_OUT_SILVER",
        count=count,
    )


def _record_processed_stage_accounting(stage: str, count: int) -> None:
    """Update stage-accounting projections for processed-record counters."""
    accounting = get_stage_accounting()
    if accounting is None or count <= 0:
        return
    if stage == "bronze":
        accounting.record_in(StageId.BRONZE.value, count)
        accounting.record_out(StageId.BRONZE.value, count)
        accounting.mark_instrumented(StageId.BRONZE.value)
        return
    if stage == "silver":
        accounting.record_out(StageId.SILVER.value, count)
        accounting.mark_instrumented(StageId.SILVER.value)
        return
    if stage == "gold":
        accounting.record_out(StageId.GOLD.value, count)
        accounting.mark_instrumented(StageId.GOLD.value)
        return
    if stage not in _SILVER_REMOVAL_REASONS:
        return
    accounting.record_removal(
        StageId.SILVER.value,
        outcome=stage,
        reason_code=_SILVER_REMOVAL_REASONS[stage],
        count=count,
    )


def _record_stage_outcome_accounting(stage: str, outcome: str, count: int) -> None:
    """Update stage-accounting for one positive stage-model outcome."""
    accounting = get_stage_accounting()
    if accounting is None:
        return
    stage_l = stage.lower()
    outcome_l = outcome.lower()
    if stage_l == "gold":
        if outcome_l in _GOLD_REMOVAL_REASONS:
            accounting.record_removal(
                StageId.GOLD.value,
                outcome=outcome_l,
                reason_code=_GOLD_REMOVAL_REASONS[outcome_l],
                count=count,
            )
        elif outcome_l in {"written", "records"}:
            accounting.record_out(StageId.GOLD.value, count)
            accounting.mark_instrumented(StageId.GOLD.value)
        return
    if stage_l == "silver" and outcome_l in _SILVER_REMOVAL_REASONS:
        accounting.record_removal(
            StageId.SILVER.value,
            outcome=outcome_l,
            reason_code=_SILVER_REMOVAL_REASONS[outcome_l],
            count=count,
        )


def _silver_filter_rejection_labels(
    details: JsonDict | None,
) -> tuple[str | None, str | None, str | None]:
    """Extract bounded silver-filter rejection labels from optional details."""
    if details is None:
        return None, None, None
    reason_code = details.get("reason_code")
    reason = reason_code if isinstance(reason_code, str) else None
    rule_type_raw = details.get("rule_type")
    if isinstance(rule_type_raw, str):
        rule_type: str | None = rule_type_raw
    elif details.get("policy_stage") == "structural":
        rule_type = "structural_policy"
    else:
        rule_type = None
    field_raw = details.get("field")
    field = field_raw if isinstance(field_raw, str) else None
    return reason, rule_type, field


class BatchMetricsRecorderService:
    """Record bounded batch-processing metrics; all methods are metrics-safe no-ops."""

    def __init__(
        self,
        metrics: MetricsPort | None,
        pipeline_label: str,
        run_type_label: str,
        pipeline_metrics: PipelineMetricsRecorder | None = None,
    ) -> None:
        """Initialize pipeline-scoped batch metrics helpers."""
        self._metrics = metrics
        self._pipeline_label = pipeline_label
        self._run_type_label = run_type_label
        self._pipeline_metrics = (
            pipeline_metrics
            if pipeline_metrics is not None
            else PipelineMetricsRecorder(metrics, pipeline_label)
        )
        self._error_count = 0

    @property
    def error_count(self) -> int:
        """Get the current error count."""
        return self._error_count

    def track_batch_size(self, stage: str, size: int) -> None:
        """Record a batch-size histogram sample for one processing stage."""
        if self._metrics:
            self._metrics.observe_histogram(
                "bioetl_batch_size_records",
                size,
                {"pipeline": self._pipeline_label, "stage": stage},
            )

    def track_records_fetched(self, count: int) -> None:
        """Record the bounded fetched-side record-flow projection."""
        self._pipeline_metrics.record_record_flow(
            run_type=self._run_type_label,
            flow_stage="fetched",
            count=count,
        )
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type_label,
            stage="input",
            outcome="fetched",
            count=count,
        )
        accounting = get_stage_accounting()
        if accounting is not None and count > 0:
            accounting.record_in(StageId.EXTRACT.value, count)
            accounting.mark_instrumented(StageId.EXTRACT.value)

    def track_batch_created(self, *, stage: str, count: int) -> None:
        """Record one successful batch-created lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="created",
            stage=stage,
            status="success",
            count=1,
            record_count=count,
        )

    def track_batch_written(self, *, stage: str, count: int) -> None:
        """Record one successful batch-written lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="written",
            stage=stage,
            status="success",
            count=1,
            record_count=count,
        )

    def track_batch_failed(self, *, stage: str, count: int = 0) -> None:
        """Record one failed batch lifecycle projection."""
        self._pipeline_metrics.record_batch_lifecycle_event(
            run_type=self._run_type_label,
            event="failed",
            stage=stage,
            status="failed",
            count=1,
            record_count=count,
        )

    def track_processed_records(self, stage: str, count: int) -> None:
        """Record processed-record counters and canonical flow projections."""
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_records_processed_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "run_type": self._run_type_label,
                },
            )
        if stage in _FLOW_ACCOUNTING_STAGES:
            self._pipeline_metrics.record_record_flow(
                run_type=self._run_type_label,
                flow_stage=stage,
                count=count,
            )
        if stage == "filtered_out":
            _record_filtered_out_stage_metrics(
                self._pipeline_metrics,
                run_type_label=self._run_type_label,
                count=count,
            )
            return
        _record_processed_stage_accounting(stage, count)

    def track_error(self, stage: str, error_type: ErrorType) -> None:
        """Record one stage-scoped error occurrence."""
        self._error_count += 1
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_errors_total",
                1,
                {
                    "pipeline": self._pipeline_label,
                    "stage": stage,
                    "error_code": error_type.value,
                },
            )

    def track_dq_validation_failure(
        self, stage: str, severity: str, count: int = 1
    ) -> None:
        """Record DQ validation failures with bounded stage/severity labels."""
        self._pipeline_metrics.record_dq_validation_failures(
            stage=stage,
            severity=severity,
            count=count,
        )

    def track_stage_records(
        self,
        *,
        stage: str,
        outcome: str,
        count: int,
    ) -> None:
        """Record one canonical stage-model outcome when the count is positive."""
        if count <= 0:
            return
        self._pipeline_metrics.record_stage_records(
            run_type=self._run_type_label,
            stage=stage,
            outcome=outcome,
            count=count,
        )
        _record_stage_outcome_accounting(stage, outcome, count)

    def track_quarantined_records(self, error_type: ErrorType, count: int) -> None:
        """Record quarantined-record counters and flow projections."""
        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_dq_records_quarantined_total",
                count,
                {
                    "pipeline": self._pipeline_label,
                    "error_type": error_type.value,
                    "run_type": self._run_type_label,
                },
            )
            self._pipeline_metrics.record_quarantine_records(
                reason=error_type.value,
                count=count,
            )
            self._pipeline_metrics.record_record_flow(
                run_type=self._run_type_label,
                flow_stage="quarantined",
                count=count,
            )
        _record_silver_removal_accounting(
            outcome="quarantined",
            reason_code=getattr(error_type, "value", str(error_type)),
            count=count,
        )

    def track_silver_filter_rejection(
        self,
        details: JsonDict | None = None,
        count: int = 1,
    ) -> None:
        """Record bounded Silver-filter reject breakdown labels.

        `message` remains display-only and is intentionally ignored here.
        """
        if not self._metrics:
            return
        reason_code, rule_type, field = _silver_filter_rejection_labels(details)
        self._pipeline_metrics.record_silver_filter_rejections(
            run_type=self._run_type_label,
            reason_code=reason_code,
            rule_type=rule_type,
            field=field,
            count=count,
        )
        _record_silver_removal_accounting(
            outcome="filtered_out",
            reason_code=reason_code or "FILTERED_OUT_SILVER",
            count=count,
        )


# Compatibility alias retained for legacy imports.
BatchMetricsRecorder = BatchMetricsRecorderService

__all__ = ["BatchMetricsRecorder", "BatchMetricsRecorderService"]
