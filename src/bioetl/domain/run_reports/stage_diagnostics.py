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


def project_stage_diagnostics(
    report: Mapping[str, object] | None,
    *,
    ledger_events: Sequence[Mapping[str, object]] | None = None,
    request_state: str | None = None,
    request_reason: str | None = None,
) -> dict[str, object]:
    """Return stage rows, coverage, and blockers for one saved run."""
    if request_state is not None:
        row = _gap_row(request_state, request_reason or "selection_required", "request")
        return _envelope([row], _INCOMPLETE)
    payload = report if isinstance(report, Mapping) else {}
    identity = _mapping(payload.get("identity"))
    execution = str(identity.get("status") or "unknown").lower()
    funnel = _mappings(payload.get("funnel"))
    timings = _mapping(payload.get("stage_timings"))
    events = [event for event in (ledger_events or ()) if isinstance(event, Mapping)]
    rows = _rows_from_funnel(funnel, timings)
    rows.extend(_rows_from_timings(timings, {str(row["stage_id"]) for row in rows}))
    rows.extend(_rows_from_events(events, {str(row["stage_id"]) for row in rows}))
    if not rows:
        reason = (
            "terminal_event_missing"
            if execution in _OPEN or execution not in _TERMINAL
            else "stage_evidence_missing"
        )
        state = _UNFINISHED if execution in _OPEN else _INCOMPLETE
        rows = [_gap_row(state, reason, "report")]
    elif execution in _OPEN:
        for row in rows:
            if row["state"] == _OK:
                row["state"] = _UNFINISHED
                row["reason"] = "terminal_event_missing"
    coverage = (
        "COMPLETE"
        if rows and all(row["state"] in {_OK, _NA} for row in rows)
        else _INCOMPLETE
    )
    return _envelope(rows, coverage)


def _envelope(rows: list[dict[str, object]], coverage: str) -> dict[str, object]:
    blockers = [dict(row) for row in rows if row["state"] not in {_OK, _NA}]
    return {
        "stage_diagnostics": rows,
        "diagnostic_coverage": coverage,
        "diagnostic_blockers": blockers,
    }


def _rows_from_funnel(
    funnel: list[Mapping[str, object]], timings: Mapping[str, object]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in funnel:
        stage_id = str(item.get("stage_id") or "unknown")
        balance = str(item.get("balance_status") or "UNKNOWN")
        if balance == "OK":
            state, reason = _OK, "stage_balanced"
        elif balance in {"DEGRADED", "FAILING"}:
            state, reason = balance, "stage_balance_" + balance.lower()
        else:
            state, reason = _INCOMPLETE, "stage_balance_unknown"
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


def _rows_from_events(
    events: Sequence[Mapping[str, object]], seen: set[str]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in events:
        kind = str(event.get("event_type") or event.get("type") or "")
        if kind not in {"stage_started", "stage_completed"}:
            continue
        stage_id = str(event.get("stage_id") or event.get("stage") or "unknown")
        if stage_id in seen:
            continue
        seen.add(stage_id)
        state = _OK if kind == "stage_completed" else _UNFINISHED
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


def _duration(value: object) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, Mapping):
        nested = value.get("duration_seconds")
        if isinstance(nested, int | float) and not isinstance(nested, bool):
            return nested
    return None


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]
