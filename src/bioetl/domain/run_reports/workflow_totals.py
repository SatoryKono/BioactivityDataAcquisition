"""Measured workflow counts and reconciliation snapshots, independent of row parsing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, SupportsIndex, SupportsInt, cast

from bioetl.domain.run_reports.models import WorkflowExecutionRow

_SUCCESS = frozenset({"success", "completed", "ok"})
_FAILED = frozenset({"failed", "error", "timeout"})
_SKIPPED = frozenset({"skipped", "skip"})


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


def _status_count(
    rows: Sequence[WorkflowExecutionRow], statuses: frozenset[str]
) -> int:
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
        **_reconciliation_totals(rows),
    }


def _snapshot_current(details: Mapping[str, object]) -> int | None:
    snapshot = details.get("source_snapshot")
    if not isinstance(snapshot, dict):
        return None
    value = snapshot.get("current_rows")
    return value if isinstance(value, int) else None


def _measured_current(
    row: WorkflowExecutionRow, details: Mapping[str, object]
) -> int | None:
    if row.status.lower() not in _SUCCESS or details.get("dry_run"):
        return None
    if details.get("source_scope") != "all_current":
        return None
    if details.get("mutation_mode") not in {"gold_scd2_expiry", "no_op"}:
        return None
    return _snapshot_current(details)


def _expired_count(details: Mapping[str, object]) -> int:
    if details.get("mutation_mode") != "gold_scd2_expiry":
        return 0
    return _as_int(details.get("orphan_rows_deleted"))


def _gold_outcomes(rows: Sequence[WorkflowExecutionRow]) -> list[WorkflowExecutionRow]:
    return [
        row
        for row in rows
        if row.reconciliation and row.reconciliation.get("source_layer") == "gold"
    ]


def _reconciliation_totals(rows: Sequence[WorkflowExecutionRow]) -> dict[str, object]:
    if not any(row.reconciliation is not None for row in rows):
        return {}
    final_by_table: dict[str, int | None] = {}
    historical_by_table: dict[str, int | None] = {}
    expired = 0
    for row in _gold_outcomes(rows):
        details = cast(dict[str, object], row.reconciliation)
        table = str(details.get("source_table") or "unknown")
        final_by_table[table] = _measured_current(row, details)
        expired += _expired_count(details)
        snapshot = details.get("source_snapshot")
        if isinstance(snapshot, dict):
            physical = snapshot.get("physical_rows")
            current = snapshot.get("current_rows")
            if isinstance(physical, int) and isinstance(current, int):
                historical_by_table[table] = physical - current
    loaded = _optional_sum(rows, "records_gold")
    excluded_values = [
        row.gold_excluded_by_contract
        for row in rows
        if row.gold_excluded_by_contract is not None
    ]
    excluded = sum(excluded_values) if excluded_values else None
    return {
        "records_gold_loaded_sum": loaded,
        "records_gold_expired_sum": expired,
        "gold_current_after_reconciliation_by_table": final_by_table,
        "written_by_pipeline": loaded,
        "contract_excluded": excluded,
        "reconciliation_deactivated": expired,
        "final_current_by_table": final_by_table,
        "historical_by_table": historical_by_table,
    }
