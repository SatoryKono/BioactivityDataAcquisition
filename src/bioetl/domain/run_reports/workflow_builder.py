"""Build workflow_run_report_v1 from plan steps and typed outcomes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from bioetl.domain.run_reports.models import WorkflowExecutionRow, WorkflowRunReport
from bioetl.domain.run_reports.workflow_reasons import (
    build_reasons_rollup,
    normalize_top_reasons,
)
from bioetl.domain.run_reports.workflow_totals import _as_int, _build_totals

_COUNT_FIELDS = (
    "records_extracted",
    "records_fetched",
    "records_bronze",
    "records_silver",
    "records_gold",
)


@dataclass(frozen=True, slots=True)
class _NormalizedExecution:
    row: WorkflowExecutionRow
    pipeline_name: str | None


@dataclass(frozen=True, slots=True)
class _RowFaults:
    error_type: object = None
    error_message: object = None
    skip_reason: object = None
    gold_excluded_by_contract: object = None


def _optional_int(source: Mapping[str, object], name: str) -> int | None:
    value = source.get(name)
    return None if value is None else _as_int(value)


def _payload_mapping(payload: object) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return payload
    if payload is None:
        return {}
    return {
        name: getattr(payload, name) for name in _COUNT_FIELDS if hasattr(payload, name)
    }


def _extract_counts(payload: object) -> dict[str, int | None]:
    source = _payload_mapping(payload)
    extracted_candidates = (
        source.get("records_extracted"),
        source.get("records_fetched"),
        source.get("records_bronze"),
    )
    extracted = next(
        (value for value in extracted_candidates if value is not None), None
    )
    return {
        "records_extracted": None if extracted is None else _as_int(extracted),
        "records_bronze": _optional_int(source, "records_bronze"),
        "records_silver": _optional_int(source, "records_silver"),
        "records_gold": _optional_int(source, "records_gold"),
    }


def _first_present(source: Mapping[str, object], *names: str) -> object:
    return next(
        (source.get(name) for name in names if source.get(name) is not None), None
    )


def _first_attribute(source: object, *names: str) -> object:
    return next(
        (getattr(source, name, None) for name in names if getattr(source, name, None)),
        None,
    )


def _mapping_counts(raw: Mapping[str, object]) -> dict[str, int | None]:
    explicit = _extract_counts(raw)
    if explicit["records_extracted"] is not None or raw.get("payload") is None:
        return explicit
    return _extract_counts(raw.get("payload"))


def _mapping_execution(raw: Mapping[str, object]) -> _NormalizedExecution:
    counts = _mapping_counts(raw)
    pipeline_name = raw.get("pipeline_name")
    return _normalized_row(
        step_id=raw.get("step_id"),
        kind=raw.get("kind"),
        status=raw.get("status"),
        pipeline_name=pipeline_name,
        counts=counts,
        pipeline_run_id=_first_present(raw, "pipeline_run_id", "child_run_id"),
        pipeline_manifest_id=_first_present(
            raw,
            "pipeline_manifest_id",
            "child_manifest_id",
        ),
        pipeline_report_ref=raw.get("pipeline_report_ref"),
        top_reasons=raw.get("top_reasons") or (),
        reconciliation=_reconciliation_details(raw.get("payload")),
        faults=_RowFaults(
            error_type=raw.get("error_type"),
            error_message=raw.get("error_message"),
            skip_reason=raw.get("skip_reason"),
            gold_excluded_by_contract=raw.get("gold_excluded_by_contract"),
        ),
    )


def _object_execution(raw: object) -> _NormalizedExecution:
    counts = _extract_counts(getattr(raw, "payload", None))
    explicit = getattr(raw, "records_extracted", None)
    counts["records_extracted"] = (
        counts["records_extracted"] if explicit is None else _as_int(explicit)
    )
    return _normalized_row(
        step_id=getattr(raw, "step_id", None),
        kind=_first_attribute(raw, "step_kind", "kind"),
        status=getattr(raw, "status", None),
        pipeline_name=getattr(raw, "pipeline_name", None),
        counts=counts,
        pipeline_run_id=_first_attribute(raw, "child_run_id", "pipeline_run_id"),
        pipeline_manifest_id=_first_attribute(
            raw,
            "child_manifest_id",
            "pipeline_manifest_id",
        ),
        pipeline_report_ref=getattr(raw, "pipeline_report_ref", None),
        top_reasons=getattr(raw, "top_reasons", ()) or (),
        reconciliation=_reconciliation_details(getattr(raw, "payload", None)),
        faults=_RowFaults(
            error_type=getattr(raw, "error_type", None),
            error_message=getattr(raw, "error_message", None),
            skip_reason=getattr(raw, "skip_reason", None),
            gold_excluded_by_contract=getattr(raw, "gold_excluded_by_contract", None),
        ),
    )


def _optional_text(value: object) -> str | None:
    return None if value in (None, "") else str(value)


def _reconciliation_details(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("transform_name") != "reconcile_foreign_keys":
        return None
    fields = (
        "source_table",
        "reference_table",
        "source_layer",
        "mutation_layer",
        "source_scope",
        "source_snapshot",
        "source_run_ids",
        "scanned_rows",
        "retained_rows",
        "orphan_rows_deleted",
        "mutation_mode",
        "mutated",
        "dry_run",
        "would_mutate",
        "quarantine_rows_written",
        "quarantine_batch_id",
    )
    return {key: payload[key] for key in fields if key in payload}


def _default_report_ref(
    report_ref: str | None,
    run_id: str | None,
    pipeline_name: str | None,
) -> str | None:
    if report_ref is not None or not run_id or not pipeline_name:
        return report_ref
    return (
        f"reports/run-reports/pipeline/{pipeline_name}/{run_id}/"
        "pipeline-run-report.json"
    )


def _normalized_row(
    *,
    step_id: object,
    kind: object,
    status: object,
    pipeline_name: object,
    counts: Mapping[str, int | None],
    pipeline_run_id: object,
    pipeline_manifest_id: object,
    pipeline_report_ref: object,
    top_reasons: object = (),
    reconciliation: dict[str, object] | None = None,
    faults: _RowFaults = _RowFaults(),
) -> _NormalizedExecution:
    name = _optional_text(pipeline_name)
    run_id = _optional_text(pipeline_run_id)
    report_ref = _default_report_ref(
        _optional_text(pipeline_report_ref),
        run_id,
        name,
    )
    reasons = normalize_top_reasons(top_reasons)
    row = WorkflowExecutionRow(
        step_id=str(step_id or ""),
        kind=_optional_text(kind),
        pipeline_name=name,
        status=str(status or "unknown"),
        records_extracted=_as_int(counts.get("records_extracted")),
        records_bronze=counts.get("records_bronze"),
        records_silver=counts.get("records_silver"),
        records_gold=counts.get("records_gold"),
        pipeline_run_id=run_id,
        pipeline_manifest_id=_optional_text(pipeline_manifest_id),
        pipeline_report_ref=report_ref,
        error_type=_optional_text(faults.error_type),
        error_message=_optional_text(faults.error_message),
        top_reasons=reasons,
        skip_reason=_optional_text(faults.skip_reason),
        reconciliation=reconciliation,
        gold_excluded_by_contract=(
            None
            if faults.gold_excluded_by_contract is None
            else _as_int(faults.gold_excluded_by_contract)
        ),
    )
    return _NormalizedExecution(row=row, pipeline_name=name)


def _normalize_execution(
    raw: Mapping[str, Any] | object,  # Any: external workflow result payload
) -> _NormalizedExecution:  # Any: report/json payload shape is dynamic
    if isinstance(raw, Mapping):
        return _mapping_execution(raw)
    return _object_execution(raw)


def _normalize_plan_step(
    step: Mapping[str, Any],  # Any: dynamic workflow plan payload
) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
    return {
        "step_id": str(step.get("step_id", "")),
        "kind": str(step.get("kind", "pipeline")),
        "pipeline_name": step.get("pipeline_name"),
        "transform_name": step.get("transform_name"),
        "depends_on": list(step.get("depends_on") or ()),
    }


def _build_index(
    normalized: Sequence[_NormalizedExecution],
) -> dict[str, dict[str, Any]]:  # Any: report/json payload shape is dynamic
    index: dict[str, dict[str, Any]] = {}  # Any: report/json payload shape is dynamic
    for item in normalized:
        if item.pipeline_name is not None:
            _append_index_row(index, item.pipeline_name, item.row)
    return index


def _append_index_row(
    index: dict[str, dict[str, Any]],  # Any: report/json payload shape is dynamic
    pipeline_name: str,
    row: WorkflowExecutionRow,
) -> None:
    bucket = index.setdefault(
        pipeline_name,
        {"records_extracted": 0, "step_ids": []},
    )
    bucket["records_extracted"] = (
        int(bucket["records_extracted"]) + row.records_extracted
    )
    bucket["step_ids"] = [*bucket["step_ids"], row.step_id]


def build_workflow_run_report(
    *,
    identity: Mapping[str, Any],  # Any: report/json payload shape is dynamic
    plan_steps: Sequence[Mapping[str, Any]],
    execution_steps: Sequence[Mapping[str, Any] | object],
) -> WorkflowRunReport:
    """Project a deterministic workflow report with extraction rollups."""
    plan = tuple(_normalize_plan_step(step) for step in plan_steps)
    normalized = tuple(_normalize_execution(raw) for raw in execution_steps)
    execution = tuple(item.row for item in normalized)
    return WorkflowRunReport(
        identity=dict(identity),
        plan_steps=plan,
        execution=execution,
        totals=_build_totals(execution, planned=len(plan) or len(execution)),
        index=_build_index(normalized),
        reasons_rollup=build_reasons_rollup(execution),
    )
