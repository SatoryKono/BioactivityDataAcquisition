"""Reason normalization helpers for workflow run reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, SupportsIndex, SupportsInt

from bioetl.domain.run_reports.models import WorkflowExecutionRow

_TOP_REASONS_LIMIT = 3
_REASONS_ROLLUP_LIMIT = 10


def normalize_top_reasons(
    raw: object,
) -> tuple[dict[str, Any], ...]:  # Any: dynamic reason payload
    """Normalize and bound child pipeline reason payloads."""
    reason_entries = _as_reason_sequence(raw)
    if reason_entries is None:
        return ()
    items = [
        item for item in (_normalize_reason(entry) for entry in reason_entries) if item
    ]
    ranked = sorted(
        items,
        key=lambda item: (-_as_int(item.get("count")), str(item.get("reason_code"))),
    )
    return tuple(ranked[:_TOP_REASONS_LIMIT])


def build_reasons_rollup(
    rows: Sequence[WorkflowExecutionRow],
) -> tuple[dict[str, Any], ...]:  # Any: aggregated reason payload
    """Aggregate bounded child reasons across workflow execution rows."""
    totals: dict[tuple[str, str | None, str | None], int] = {}
    for row in rows:
        for item in row.top_reasons:
            key = _reason_key(item)
            totals[key] = totals.get(key, 0) + _as_int(item.get("count"))
    ranked = sorted(totals.items(), key=lambda entry: (-entry[1], entry[0][0]))
    return tuple(
        {
            "reason_code": code,
            "outcome": outcome,
            "reason_family": family,
            "count": count,
        }
        for (code, outcome, family), count in ranked[:_REASONS_ROLLUP_LIMIT]
    )


def _as_reason_sequence(raw: object) -> Sequence[object] | None:
    """Narrow a dynamic reason payload to the supported sequence contract."""
    if not isinstance(raw, Sequence):
        return None
    if isinstance(raw, (str, bytes)):
        return None
    return raw


def _normalize_reason(
    entry: object,
) -> dict[str, Any] | None:  # Any: normalized reason payload
    if not isinstance(entry, Mapping):
        return None
    code = entry.get("reason_code")
    if code in (None, ""):
        return None
    return {
        "reason_code": str(code),
        "outcome": entry.get("outcome"),
        "reason_family": entry.get("reason_family"),
        "count": _as_int(entry.get("count")),
    }


def _reason_key(
    item: Mapping[str, Any],  # Any: dynamic reason payload
) -> tuple[str, str | None, str | None]:
    return (
        str(item.get("reason_code")),
        _optional_reason_text(item.get("outcome")),
        _optional_reason_text(item.get("reason_family")),
    )


def _optional_reason_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def resolve_child_workflow_binding(
    bound_identity: object,
    child_identity: object,
    step_id: object,
) -> tuple[str, str, object, object, object] | str:
    """Return parent coordinates, or a gap code when the child binding is incomplete."""
    if not isinstance(bound_identity, dict) or not isinstance(child_identity, dict):
        return "binding_not_recorded"
    name = bound_identity.get("workflow_name")
    run_id = bound_identity.get("workflow_run_id")
    if not isinstance(name, str) or not isinstance(run_id, str):
        return "identity_not_recorded"
    child_run_id = child_identity.get("run_id")
    child_pipeline_name = child_identity.get("pipeline_name")
    if (
        not isinstance(step_id, str)
        or not isinstance(child_run_id, str)
        or not isinstance(child_pipeline_name, str)
    ):
        return "child_identity_not_recorded"
    return (
        name,
        run_id,
        step_id,
        child_run_id,
        child_pipeline_name,
    )


def _parent_identity_matches(
    parent_identity: object,
    workflow_name: str,
    workflow_run_id: str,
) -> bool:
    if not isinstance(parent_identity, dict):
        return False
    if parent_identity.get("workflow_name") != workflow_name:
        return False
    return parent_identity.get("workflow_run_id") == workflow_run_id


def _step_binds_child(
    step: object,
    step_id: object,
    child_run_id: object,
    child_pipeline_name: object,
) -> bool:
    if not isinstance(step, dict):
        return False
    if step.get("step_id") != step_id:
        return False
    if step.get("pipeline_run_id") != child_run_id:
        return False
    return step.get("pipeline_name") == child_pipeline_name


def _execution_binds_child(
    parent_execution: object,
    step_id: object,
    child_run_id: object,
    child_pipeline_name: object,
) -> bool:
    if not isinstance(parent_execution, list):
        return False
    return any(
        _step_binds_child(step, step_id, child_run_id, child_pipeline_name)
        for step in parent_execution
    )


def parent_binding_gap(
    *,
    workflow_name: str,
    workflow_run_id: str,
    parent_identity: object,
    parent_execution: object,
    step_id: object,
    child_run_id: object,
    child_pipeline_name: object,
) -> str | None:
    """Return why a loaded parent does not apply to this child."""
    if not _parent_identity_matches(parent_identity, workflow_name, workflow_run_id):
        return "identity_mismatch"
    if not _execution_binds_child(
        parent_execution,
        step_id,
        child_run_id,
        child_pipeline_name,
    ):
        return "child_binding_mismatch"
    return None


def _as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if not isinstance(
        value,
        (str, bytes, bytearray, SupportsInt, SupportsIndex),
    ):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default
