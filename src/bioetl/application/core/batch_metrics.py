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
            self._pipeline_metrics.record_stage_records(
                run_type=self._run_type_label,
                stage="transform",
                outcome="filtered_out",
                count=count,
            )
            self._pipeline_metrics.record_stage_records(
                run_type=self._run_type_label,
                stage="silver",
                outcome="filtered_out",
                count=count,
            )
            accounting = get_stage_accounting()
            if accounting is not None and count > 0:
                accounting.record_removal(
                    StageId.SILVER.value,
                    outcome="filtered_out",
                    reason_code="FILTERED_OUT_SILVER",
                    count=count,
                )
        else:
            accounting = get_stage_accounting()
            if accounting is not None and count > 0:
                if stage == "bronze":
                    accounting.record_in(StageId.BRONZE.value, count)
                    accounting.record_out(StageId.BRONZE.value, count)
                    accounting.mark_instrumented(StageId.BRONZE.value)
                elif stage == "silver":
                    accounting.record_out(StageId.SILVER.value, count)
                    accounting.mark_instrumented(StageId.SILVER.value)
                elif stage == "gold":
                    accounting.record_out(StageId.GOLD.value, count)
                    accounting.mark_instrumented(StageId.GOLD.value)
                elif stage in {"quarantined", "deduplicated", "skipped"}:
                    outcome = stage
                    reason = {
                        "quarantined": "SCHEMA_VALIDATION_FAILURE",
                        "deduplicated": "DEDUP_KEY_COLLISION",
                        "skipped": "UNKNOWN_REASON",
                    }.get(stage, "UNKNOWN_REASON")
                    accounting.record_removal(
                        StageId.SILVER.value,
                        outcome=outcome,
                        reason_code=reason,
                        count=count,
                    )

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
        accounting = get_stage_accounting()
        if accounting is None:
            return
        stage_l = stage.lower()
        outcome_l = outcome.lower()
        if stage_l == "gold":
            if outcome_l in {
                "excluded_by_contract",
                "quarantined",
                "skipped",
                "deduplicated",
            }:
                reason = {
                    "excluded_by_contract": "gold_contract_schema_failure",
                    "quarantined": "gold_semantic_business_exclusion",
                    "skipped": "UNKNOWN_REASON",
                    "deduplicated": "DEDUP_KEY_COLLISION",
                }[outcome_l]
                accounting.record_removal(
                    StageId.GOLD.value,
                    outcome=outcome_l,
                    reason_code=reason,
                    count=count,
                )
            elif outcome_l in {"written", "records"}:
                accounting.record_out(StageId.GOLD.value, count)
                accounting.mark_instrumented(StageId.GOLD.value)
        elif stage_l == "silver" and outcome_l in {
            "filtered_out",
            "quarantined",
            "skipped",
            "deduplicated",
        }:
            reason = {
                "filtered_out": "FILTERED_OUT_SILVER",
                "quarantined": "SCHEMA_VALIDATION_FAILURE",
                "skipped": "UNKNOWN_REASON",
                "deduplicated": "DEDUP_KEY_COLLISION",
            }[outcome_l]
            accounting.record_removal(
                StageId.SILVER.value,
                outcome=outcome_l,
                reason_code=reason,
                count=count,
            )

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
        accounting = get_stage_accounting()
        if accounting is not None and count > 0:
            accounting.record_removal(
                StageId.SILVER.value,
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
        reason_code: str | None = None
        rule_type: str | None = None
        field: str | None = None

        if details is not None:
            maybe_reason_code = details.get("reason_code")
            if isinstance(maybe_reason_code, str):
                reason_code = maybe_reason_code

            maybe_rule_type = details.get("rule_type")
            if isinstance(maybe_rule_type, str):
                rule_type = maybe_rule_type
            elif details.get("policy_stage") == "structural":
                rule_type = "structural_policy"

            maybe_field = details.get("field")
            if isinstance(maybe_field, str):
                field = maybe_field
        self._pipeline_metrics.record_silver_filter_rejections(
            run_type=self._run_type_label,
            reason_code=reason_code,
            rule_type=rule_type,
            field=field,
            count=count,
        )
        accounting = get_stage_accounting()
        if accounting is not None and count > 0:
            accounting.record_removal(
                StageId.SILVER.value,
                outcome="filtered_out",
                reason_code=reason_code or "FILTERED_OUT_SILVER",
                count=count,
            )


# Compatibility alias retained for legacy imports.
BatchMetricsRecorder = BatchMetricsRecorderService

__all__ = ["BatchMetricsRecorder", "BatchMetricsRecorderService"]
