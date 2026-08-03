"""Reason normalization helpers for workflow run reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, SupportsIndex, SupportsInt, TypeGuard

from bioetl.domain.run_reports.models import WorkflowExecutionRow


def normalize_top_reasons(
    raw: object,
) -> tuple[dict[str, Any], ...]:  # Any: dynamic reason payload
    """Normalize and bound child pipeline reason payloads."""
    if not _is_reason_sequence(raw):
        return ()
    items = (_normalize_reason(entry) for entry in raw)
    return tuple(item for item in items if item is not None)[:3]


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
        for (code, outcome, family), count in ranked[:10]
    )


def _is_reason_sequence(raw: object) -> TypeGuard[Sequence[object]]:
    return isinstance(raw, Sequence) and not isinstance(raw, (str, bytes))


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
