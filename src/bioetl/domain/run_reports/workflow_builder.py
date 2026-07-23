"""Build workflow_run_report_v1 from plan steps and typed outcomes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from bioetl.domain.run_reports.models import WorkflowExecutionRow, WorkflowRunReport

_COUNT_FIELDS = (
    "records_extracted",
    "records_fetched",
    "records_bronze",
    "records_silver",
    "records_gold",
)
_SUCCESS = frozenset({"success", "completed", "ok"})
_FAILED = frozenset({"failed", "error", "timeout"})
_SKIPPED = frozenset({"skipped", "skip"})


@dataclass(frozen=True, slots=True)
class _NormalizedExecution:
    row: WorkflowExecutionRow
    pipeline_name: str | None


def _as_int(value: object, default: int = 0) -> int:
    try:
        return default if value is None else int(value)
    except (TypeError, ValueError):
        return default


def _optional_int(source: Mapping[str, object], name: str) -> int | None:
    value = source.get(name)
    return None if value is None else _as_int(value)


def _payload_mapping(payload: object) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return payload
    if payload is None:
        return {}
    return {
        name: getattr(payload, name)
        for name in _COUNT_FIELDS
        if hasattr(payload, name)
    }


def _extract_counts(payload: object) -> dict[str, int | None]:
    source = _payload_mapping(payload)
    extracted_candidates = (
        source.get("records_extracted"),
        source.get("records_fetched"),
        source.get("records_bronze"),
    )
    extracted = next((value for value in extracted_candidates if value is not None), 0)
    return {
        "records_extracted": _as_int(extracted),
        "records_bronze": _optional_int(source, "records_bronze"),
        "records_silver": _optional_int(source, "records_silver"),
        "records_gold": _optional_int(source, "records_gold"),
    }


def _first_present(source: Mapping[str, object], *names: str) -> object:
    return next((source.get(name) for name in names if source.get(name) is not None), None)


def _mapping_counts(raw: Mapping[str, object]) -> dict[str, int | None]:
    explicit = _extract_counts(raw)
    if explicit["records_extracted"] != 0 or raw.get("payload") is None:
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
        error_type=raw.get("error_type"),
        error_message=raw.get("error_message"),
    )


def _object_execution(raw: object) -> _NormalizedExecution:
    counts = _extract_counts(getattr(raw, "payload", None))
    explicit = getattr(raw, "records_extracted", None)
    counts["records_extracted"] = (
        counts["records_extracted"] if explicit is None else _as_int(explicit)
    )
    return _normalized_row(
        step_id=getattr(raw, "step_id", None),
        kind=getattr(raw, "step_kind", None) or getattr(raw, "kind", None),
        status=getattr(raw, "status", None),
        pipeline_name=getattr(raw, "pipeline_name", None),
        counts=counts,
        pipeline_run_id=getattr(raw, "child_run_id", None)
        or getattr(raw, "pipeline_run_id", None),
        pipeline_manifest_id=getattr(raw, "child_manifest_id", None)
        or getattr(raw, "pipeline_manifest_id", None),
        pipeline_report_ref=getattr(raw, "pipeline_report_ref", None),
        error_type=getattr(raw, "error_type", None),
        error_message=getattr(raw, "error_message", None),
    )


def _optional_text(value: object) -> str | None:
    return None if value in (None, "") else str(value)


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
    error_type: object,
    error_message: object,
) -> _NormalizedExecution:
    name = _optional_text(pipeline_name)
    row = WorkflowExecutionRow(
        step_id=str(step_id or ""),
        kind=_optional_text(kind),
        pipeline_name=name,
        status=str(status or "unknown"),
        records_extracted=_as_int(counts.get("records_extracted")),
        records_bronze=counts.get("records_bronze"),
        records_silver=counts.get("records_silver"),
        records_gold=counts.get("records_gold"),
        pipeline_run_id=_optional_text(pipeline_run_id),
        pipeline_manifest_id=_optional_text(pipeline_manifest_id),
        pipeline_report_ref=_optional_text(pipeline_report_ref),
        error_type=_optional_text(error_type),
        error_message=_optional_text(error_message),
    )
    return _NormalizedExecution(row=row, pipeline_name=name)


def _normalize_execution(raw: Mapping[str, Any] | object) -> _NormalizedExecution:  # Any: report/json payload shape is dynamic
    if isinstance(raw, Mapping):
        return _mapping_execution(raw)
    return _object_execution(raw)


def _normalize_plan_step(step: Mapping[str, Any]) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
    return {
        "step_id": str(step.get("step_id", "")),
        "kind": str(step.get("kind", "pipeline")),
        "pipeline_name": step.get("pipeline_name"),
        "transform_name": step.get("transform_name"),
        "depends_on": list(step.get("depends_on") or ()),
    }


def _status_count(rows: Sequence[WorkflowExecutionRow], statuses: frozenset[str]) -> int:
    return sum(row.status.lower() in statuses for row in rows)


def _optional_sum(rows: Sequence[WorkflowExecutionRow], field_name: str) -> int | None:
    values = [getattr(row, field_name) for row in rows]
    present = [int(value) for value in values if value is not None]
    return sum(present) if present else None


def _build_totals(
    rows: Sequence[WorkflowExecutionRow],
    *,
    planned: int,
) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
    return {
        "steps_planned": planned,
        "steps_succeeded": _status_count(rows, _SUCCESS),
        "steps_failed": _status_count(rows, _FAILED),
        "steps_skipped": _status_count(rows, _SKIPPED),
        "records_extracted_sum": sum(row.records_extracted for row in rows),
        "records_silver_sum": _optional_sum(rows, "records_silver"),
        "records_gold_sum": _optional_sum(rows, "records_gold"),
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
    bucket["records_extracted"] = int(bucket["records_extracted"]) + row.records_extracted
    bucket["step_ids"] = [*bucket["step_ids"], row.step_id]


def build_workflow_run_report(
    *,
    identity: Mapping[str, Any],  # Any: report/json payload shape is dynamic
    plan_steps: Sequence[Mapping[str, Any]],  # Any: report/json payload shape is dynamic
    execution_steps: Sequence[Mapping[str, Any] | object],  # Any: report/json payload shape is dynamic
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
    )
