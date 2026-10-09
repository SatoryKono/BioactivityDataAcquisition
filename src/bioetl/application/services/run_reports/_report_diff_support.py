"""Diff helpers for persisted pipeline run reports (Wave-4-style seam)."""

from __future__ import annotations

from typing import Any

MappingLike = dict[str, Any] | Any  # Any: decoded external JSON payload
ReportPayload = dict[str, Any]  # Any: decoded report JSON payload


def _as_mapping(value: MappingLike) -> ReportPayload:
    if isinstance(value, dict):
        return value
    raise TypeError("report payload must be a mapping")


def _int(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


def diff_pipeline_reports(left: MappingLike, right: MappingLike) -> ReportPayload:
    """Compute funnel and reason deltas between two pipeline report payloads."""
    left_payload = _as_mapping(left)
    right_payload = _as_mapping(right)
    return {
        "left_run_id": (left_payload.get("identity") or {}).get("run_id"),
        "right_run_id": (right_payload.get("identity") or {}).get("run_id"),
        "funnel_delta": _funnel_delta(left_payload, right_payload),
        "reasons_delta": _reasons_delta(left_payload, right_payload),
    }


def _funnel_rows(payload: ReportPayload) -> dict[str, ReportPayload]:
    return {
        str(row.get("stage_id")): row
        for row in payload.get("funnel") or []
        if isinstance(row, dict)
    }


def _funnel_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic funnel delta rows
    left_rows = _funnel_rows(left)
    right_rows = _funnel_rows(right)
    stages = sorted(set(left_rows) | set(right_rows))
    return [
        _stage_delta(stage, left_rows.get(stage, {}), right_rows.get(stage, {}))
        for stage in stages
    ]


def _stage_delta(
    stage: str,
    left: dict[str, Any],  # Any: dynamic funnel row
    right: dict[str, Any],  # Any: dynamic funnel row
) -> dict[str, Any]:  # Any: dynamic stage delta payload
    return {
        "stage_id": stage,
        "records_in_delta": _int(right.get("records_in"))
        - _int(left.get("records_in")),
        "records_out_delta": _int(right.get("records_out"))
        - _int(left.get("records_out")),
        "removed_total_delta": _int(right.get("removed_total"))
        - _int(left.get("removed_total")),
    }


def _reason_counts(payload: ReportPayload) -> dict[str, int]:
    items = payload.get("reasons_top_n") or []
    return {
        str(i.get("reason_code")): _int(i.get("count"))
        for i in items
        if isinstance(i, dict)
    }


def _reasons_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic reason delta rows
    left_counts = _reason_counts(left)
    right_counts = _reason_counts(right)
    return [
        {
            "reason_code": code,
            "count_delta": right_counts.get(code, 0) - left_counts.get(code, 0),
        }
        for code in sorted(set(left_counts) | set(right_counts))
    ]
