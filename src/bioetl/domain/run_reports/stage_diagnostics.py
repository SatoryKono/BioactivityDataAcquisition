"""Project saved funnel, timings, and ledger events into stage diagnostics.

The projector does not read clocks or Prometheus. A missing count stays null.
An explicit zero stays zero. SUCCESS does not invent successful stages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

_INCOMPLETE = "INCOMPLETE"
_UNFINISHED = "UNFINISHED"
_OK = "OK"
_NA = "N/A"
_TERMINAL = {"success", "failed", "shutdown", "dry_run"}
_OPEN = {"running", "started"}


def _requested_gap_row(
    request_state: str, request_reason: str | None
) -> dict[str, object]:
    """Project the request-selection gap row."""
    return _gap_row(request_state, request_reason or "selection_required", "request")


def _report_payload(report: Mapping[str, object] | None) -> Mapping[str, object]:
    """Coerce the saved report to a mapping payload."""
    if isinstance(report, Mapping):
        return report
    return {}


def _ledger_event_mappings(
    ledger_events: Sequence[Mapping[str, object]] | None,
) -> list[Mapping[str, object]]:
    """Filter ledger events down to mapping payloads."""
    return [event for event in (ledger_events or ()) if isinstance(event, Mapping)]


def _collect_stage_rows(
    *,
    payload: Mapping[str, object],
    ledger_events: Sequence[Mapping[str, object]] | None,
) -> list[dict[str, object]]:
    """Assemble funnel, timing, and ledger stage rows."""
    funnel = _mappings(payload.get("funnel"))
    timings = _mapping(payload.get("stage_timings"))
    events = _ledger_event_mappings(ledger_events)
    rows = _rows_from_funnel(funnel, timings)
    rows.extend(_rows_from_timings(timings, {str(row["stage_id"]) for row in rows}))
    rows.extend(_rows_from_events(events, {str(row["stage_id"]) for row in rows}))
    return rows


def _empty_rows_gap(execution: str) -> dict[str, object]:
    """Project the gap row when no stage evidence exists."""
    reason = (
        "terminal_event_missing"
        if execution in _OPEN or execution not in _TERMINAL
        else "stage_evidence_missing"
    )
    if execution in _OPEN:
        return _gap_row(_UNFINISHED, reason, "report")
    return _gap_row(_INCOMPLETE, reason, "report")


def _mark_open_execution_rows(rows: list[dict[str, object]]) -> None:
    """Demote OK rows while the execution is still open."""
    for row in rows:
        if row["state"] == _OK:
            row["state"] = _UNFINISHED
            row["reason"] = "terminal_event_missing"


def _diagnostic_coverage(rows: list[dict[str, object]]) -> str:
    """Derive COMPLETE coverage when every row is terminally resolved."""
    if rows and all(row["state"] in {_OK, _NA} for row in rows):
        return "COMPLETE"
    return _INCOMPLETE


def project_stage_diagnostics(
    report: Mapping[str, object] | None,
    *,
    ledger_events: Sequence[Mapping[str, object]] | None = None,
    request_state: str | None = None,
    request_reason: str | None = None,
) -> dict[str, object]:
    """Return stage rows, coverage, and blockers for one saved run."""
    if request_state is not None:
        return _envelope(
            [_requested_gap_row(request_state, request_reason)], _INCOMPLETE
        )
    payload = _report_payload(report)
    identity = _mapping(payload.get("identity"))
    execution = str(identity.get("status") or "unknown").lower()
    rows = _collect_stage_rows(payload=payload, ledger_events=ledger_events)
    if not rows:
        rows = [_empty_rows_gap(execution)]
    elif execution in _OPEN:
        _mark_open_execution_rows(rows)
    return _envelope(rows, _diagnostic_coverage(rows))


def _envelope(rows: list[dict[str, object]], coverage: str) -> dict[str, object]:
    blockers = [dict(row) for row in rows if row["state"] not in {_OK, _NA}]
    return {
        "stage_diagnostics": rows,
        "diagnostic_coverage": coverage,
        "diagnostic_blockers": blockers,
    }


def _funnel_balance_state(balance: str) -> tuple[str, str]:
    """Resolve the state/reason pair for one funnel balance status."""
    if balance == "OK":
        return _OK, "stage_balanced"
    if balance in {"DEGRADED", "FAILING"}:
        return balance, "stage_balance_" + balance.lower()
    return _INCOMPLETE, "stage_balance_unknown"


def _rows_from_funnel(
    funnel: list[Mapping[str, object]], timings: Mapping[str, object]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in funnel:
        stage_id = str(item.get("stage_id") or "unknown")
        balance = str(item.get("balance_status") or "UNKNOWN")
        state, reason = _funnel_balance_state(balance)
        rows.append(
            _stage_row(
                stage_id,
                state,
                reason,
                records_in=_count(item.get("records_in")),
                records_out=_count(item.get("records_out")),
                duration_seconds=_duration(timings.get(stage_id)),
                source="report.funnel",
            )
        )
    return rows


def _rows_from_timings(
    timings: Mapping[str, object], seen: set[str]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for stage_id, value in timings.items():
        if str(stage_id) in seen:
            continue
        rows.append(
            _stage_row(
                str(stage_id),
                _INCOMPLETE,
                "stage_counts_unconfirmed",
                records_in=None,
                records_out=None,
                duration_seconds=_duration(value),
                source="report.stage_timings",
            )
        )
    return rows


def _lifecycle_event_kind(event: Mapping[str, object]) -> str | None:
    """Return the lifecycle kind for stage start/complete events."""
    kind = str(event.get("event_type") or event.get("type") or "")
    if kind not in {"stage_started", "stage_completed"}:
        return None
    return kind


def _lifecycle_event(event: Mapping[str, object]) -> tuple[str, str, str] | None:
    """Return the (stage_id, state, kind) triple for lifecycle events."""
    kind = _lifecycle_event_kind(event)
    if kind is None:
        return None
    stage_id = str(event.get("stage_id") or event.get("stage") or "unknown")
    if kind == "stage_completed":
        return stage_id, _OK, kind
    return stage_id, _UNFINISHED, kind


def _rows_from_events(
    events: Sequence[Mapping[str, object]], seen: set[str]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in events:
        lifecycle = _lifecycle_event(event)
        if lifecycle is None:
            continue
        stage_id, state, kind = lifecycle
        if stage_id in seen:
            continue
        seen.add(stage_id)
        rows.append(
            _stage_row(
                stage_id,
                state,
                kind,
                records_in=_count(event.get("records_in")),
                records_out=_count(event.get("records_out")),
                duration_seconds=_duration(event.get("duration_seconds")),
                source="ledger",
            )
        )
    return rows


def _stage_row(
    stage_id: str,
    state: str,
    reason: str,
    *,
    records_in: int | None,
    records_out: int | None,
    duration_seconds: float | int | None,
    source: str,
) -> dict[str, object]:
    return {
        "stage_id": stage_id,
        "state": state,
        "reason": reason,
        "records_in": records_in,
        "records_out": records_out,
        "duration_seconds": duration_seconds,
        "source": source,
    }


def _gap_row(state: str, reason: str, source: str) -> dict[str, object]:
    return _stage_row(
        "—",
        state,
        reason,
        records_in=None,
        records_out=None,
        duration_seconds=None,
        source=source,
    )


def _count(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _nested_duration(value: Mapping[str, object]) -> float | int | None:
    """Extract a numeric duration_seconds payload from a mapping."""
    nested = value.get("duration_seconds")
    if isinstance(nested, int | float) and not isinstance(nested, bool):
        return nested
    return None


def _duration(value: object) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, Mapping):
        return _nested_duration(value)
    return None


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]
