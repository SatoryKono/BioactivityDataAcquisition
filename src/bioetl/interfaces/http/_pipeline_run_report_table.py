"""Pipeline run report table shaping for HealthServer / Run Explorer.

Keeps Grafana Infinity table panels (e.g. panel 3015) on stable
parameter/value rows and HTTP 200 empty shells instead of QUERY_ERROR.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

# Canonical reconciliation key order for Run Explorer panel 3015 (REC-04).
_RECONCILIATION_ROW_ORDER: tuple[str, ...] = (
    "silver_accounted",
    "silver_delta",
    "silver_vs_bronze_status",
    "gold_accounted",
    "gold_delta",
    "gold_vs_silver_status",
)

# Grafana selector sentinels for "no concrete run selected" (never a real run_id).
_UNRESOLVED_RUN_ID_SENTINELS = frozenset(
    {
        "",
        "-",
        "all",
        "All",
        "$__all",
        "unknown",
        "None",
        "null",
    }
)


def _is_unresolved_run_scope(run_id: str) -> bool:
    """Return True when run_id is a dashboard no-selection sentinel."""
    token = run_id.strip()
    return token in _UNRESOLVED_RUN_ID_SENTINELS


def _empty_pipeline_run_report_shell(
    *,
    run_id: str,
    pipeline: str,
    status: str,
    message: str,
) -> dict[str, object]:
    """Empty report shell for Grafana table root_selectors (no QUERY_ERROR)."""
    return {
        "status": status,
        "message": message,
        "run_id": run_id,
        "pipeline": pipeline,
        # Match pipeline_run_report_v1 keys used by Run Explorer panels.
        "funnel": [],
        "reasons_top_n": [],
        "reconciliation": [],
        "artifacts": [],
        "schema_version": "pipeline_run_report_v1",
    }


def _unresolved_pipeline_run_report_shell(
    *,
    run_id: str,
    pipeline: str,
) -> dict[str, object]:
    """Empty shell when Grafana run_id is a no-selection sentinel."""
    return _empty_pipeline_run_report_shell(
        run_id=run_id,
        pipeline=pipeline,
        status="unresolved_scope",
        message="run_id not selected; pick a run from Inspect Recent Runs",
    )


def _not_found_pipeline_run_report_shell(
    *,
    run_id: str,
    pipeline: str,
) -> dict[str, object]:
    """Empty shell for missing report artifacts (HTTP 200, not 404).

    Infinity/Grafana treats HTTP 404 as QUERY_ERROR on table panels; operator
    No data is preferred (#7650 / REC-02).
    """
    return _empty_pipeline_run_report_shell(
        run_id=run_id,
        pipeline=pipeline,
        status="not_found",
        message="pipeline run report not found",
    )


def _table_shape_pipeline_run_report(
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize nested report sections for Grafana Infinity table selectors.

    ``reconciliation`` is stored as an object in pipeline_run_report_v1 files.
    Run Explorer panel 3015 uses root_selector=reconciliation on a table panel,
    so the HTTP surface exposes a list of {parameter, value} rows. Values are
    strings because Infinity requires one stable field type when numeric
    accounting values and textual reconciliation verdicts share the column.
    """
    recon = payload.get("reconciliation")
    if not isinstance(recon, dict):
        return payload
    shaped = dict(payload)
    ordered_keys = [key for key in _RECONCILIATION_ROW_ORDER if key in recon] + sorted(
        key for key in recon if key not in _RECONCILIATION_ROW_ORDER
    )
    shaped["reconciliation"] = [
        {"parameter": str(key), "value": str(recon[key])} for key in ordered_keys
    ]
    return shaped


_RANGE_PAD = timedelta(minutes=5)


def _parse_iso_to_ms(value: object) -> int | None:
    """Parse an ISO-8601 timestamp to Unix milliseconds."""
    if not isinstance(value, str) or not value.strip():
        return None
    token = value.strip()
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def _parse_grafana_ms(value: object) -> int | None:
    """Parse Grafana ${__from}/${__to} epoch-ms query parameters."""
    if value is None:
        return None
    token = str(value).strip()
    if not token:
        return None
    try:
        return int(token)
    except ValueError:
        return None


def _coverage_offset_outside(
    *,
    started_ms: int,
    end_ms: int,
    grafana_from_ms: int,
    grafana_to_ms: int,
) -> tuple[str, str]:
    """Describe a run that is not fully inside the Grafana window."""
    if end_ms < grafana_from_ms:
        hours = (grafana_from_ms - end_ms) / 3_600_000
        return "outside", f"{hours:.1f}h before window"
    if started_ms > grafana_to_ms:
        hours = (started_ms - grafana_to_ms) / 3_600_000
        return "outside", f"{hours:.1f}h after window"
    return "partial", "overlaps window"


def _coverage_fields(
    *,
    started_ms: int | None,
    completed_ms: int | None,
    grafana_from_ms: int | None,
    grafana_to_ms: int | None,
    status: str,
) -> tuple[str, str]:
    """Return (covers_selected_run, coverage_offset) for the compact summary."""
    if status == "unresolved_scope":
        return "select_run", ""
    if status == "not_found":
        return "not_found", ""
    if started_ms is None:
        return "unknown", ""
    if grafana_from_ms is None or grafana_to_ms is None:
        return "range_unspecified", ""
    end_ms = completed_ms if completed_ms is not None else started_ms
    if started_ms >= grafana_from_ms and end_ms <= grafana_to_ms:
        return "yes", "0h"
    return _coverage_offset_outside(
        started_ms=started_ms,
        end_ms=end_ms,
        grafana_from_ms=grafana_from_ms,
        grafana_to_ms=grafana_to_ms,
    )


def _excluded_by_contract_count(removals: object) -> int:
    """Sum excluded_by_contract counts from one stage's removals list."""
    total = 0
    if not isinstance(removals, list):
        return total
    for item in removals:
        if not isinstance(item, dict):
            continue
        if item.get("outcome") != "excluded_by_contract":
            continue
        count = item.get("count")
        if isinstance(count, int):
            total += count
    return total


def _funnel_gold_and_excluded(funnel: object) -> tuple[object, int]:
    """Extract gold records_out and excluded_by_contract counts from funnel stages."""
    gold_out: object = ""
    excluded = 0
    if not isinstance(funnel, list):
        return gold_out, excluded
    for stage in funnel:
        if not isinstance(stage, dict):
            continue
        if stage.get("stage_id") == "gold":
            gold_out = stage.get("records_out")
        excluded += _excluded_by_contract_count(stage.get("removals"))
    return gold_out, excluded


def _padded_range_ms(
    started_ms: int | None, completed_ms: int | None
) -> tuple[str, str]:
    """Return padded from/to epoch-ms strings for Grafana range links."""
    if started_ms is None:
        return "", ""
    pad_ms = int(_RANGE_PAD.total_seconds() * 1000)
    end_ms = completed_ms if completed_ms is not None else started_ms
    return str(started_ms - pad_ms), str(end_ms + pad_ms)


def _identity_summary_fields(
    payload: dict[str, object],
) -> tuple[dict[str, object], str, str, str, str]:
    """Return identity dict plus run_id/status/started_at/completed_at strings."""
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        identity = {}
    run_id = str(identity.get("run_id") or payload.get("run_id") or "")
    status = str(identity.get("status") or payload.get("status") or "")
    started_at = str(identity.get("started_at") or "")
    completed_at = str(identity.get("completed_at") or "")
    return identity, run_id, status, started_at, completed_at


def _summary_rows_pipeline_run_report(
    payload: dict[str, object],
    *,
    grafana_from: object = None,
    grafana_to: object = None,
) -> dict[str, object]:
    """Compact selected-run projection for entry-dashboard summary tables.

    ``rows`` is the parameter/value shape used by existing Infinity tables.
    ``summary`` is a one-row wide table so Grafana data links can set
    ``from``/``to`` to started_at-5m .. completed_at+5m without rewriting
    ``$__from`` silently.
    """
    identity, run_id, status, started_at, completed_at = _identity_summary_fields(
        payload
    )
    gold_out, excluded = _funnel_gold_and_excluded(payload.get("funnel"))
    started_ms = _parse_iso_to_ms(started_at)
    completed_ms = _parse_iso_to_ms(completed_at)
    from_ms, to_ms = _padded_range_ms(started_ms, completed_ms)
    covers, offset = _coverage_fields(
        started_ms=started_ms,
        completed_ms=completed_ms,
        grafana_from_ms=_parse_grafana_ms(grafana_from),
        grafana_to_ms=_parse_grafana_ms(grafana_to),
        status=status,
    )
    set_range = "Set range to run (started_at-5m .. completed_at+5m)"
    summary_row = {
        "run_id": run_id,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "gold_records_out": str(gold_out),
        "excluded_by_contract": str(excluded),
        "covers_selected_run": covers,
        "coverage_offset": offset,
        "from_ms": str(from_ms),
        "to_ms": str(to_ms),
        "set_range_to_run": set_range,
    }
    rows = [{"parameter": key, "value": value} for key, value in summary_row.items()]
    return {
        "schema_version": "pipeline_run_report_v1",
        "view": "summary",
        "rows": rows,
        "summary": [summary_row],
        "status": status or "ok",
        "run_id": run_id,
        "pipeline": identity.get("pipeline_name") or payload.get("pipeline"),
    }
