"""Stage-accounting helpers for batch metrics recording (TD-R-05 / #6681)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.run_reports.context import get_stage_accounting
from bioetl.domain.run_reports.models import StageId

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict

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


def _record_batch_lifecycle_event(
    pipeline_metrics: PipelineMetricsRecorder,
    *,
    run_type_label: str,
    event: str,
    stage: str,
    status: str,
    count: int = 1,
    record_count: int = 0,
) -> None:
    """Project one batch lifecycle event through the pipeline metrics recorder."""
    pipeline_metrics.record_batch_lifecycle_event(
        run_type=run_type_label,
        event=event,
        stage=stage,
        status=status,
        count=count,
        record_count=record_count,
    )


__all__ = [
    "_FLOW_ACCOUNTING_STAGES",
    "_GOLD_REMOVAL_REASONS",
    "_SILVER_REMOVAL_REASONS",
    "_record_batch_lifecycle_event",
    "_record_filtered_out_stage_metrics",
    "_record_processed_stage_accounting",
    "_record_silver_removal_accounting",
    "_record_stage_outcome_accounting",
    "_silver_filter_rejection_labels",
]
