"""Pipeline run report table shaping for HealthServer / Run Explorer.

Keeps Grafana Infinity table panels (e.g. panel 3015) on stable
parameter/value rows and HTTP 200 empty shells instead of QUERY_ERROR.
"""

from __future__ import annotations

import json
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

# pipeline_run_report_v1.layers required keys (D6-IA-02).
_LAYER_ROW_ORDER: tuple[str, ...] = (
    "bronze_records",
    "silver_valid",
    "silver_filtered_out",
    "silver_quarantined",
    "silver_skipped",
    "silver_deduplicated",
    "gold_written",
    "gold_excluded_by_contract",
    "gold_quarantined",
    "gold_skipped",
    "gold_deduplicated",
)

# Optional failure object keys (D6-IA-01).
_FAILURE_ROW_ORDER: tuple[str, ...] = (
    "error_type",
    "error_message",
    "failed_stage",
    "exit_hint",
)

# Report identity keys surfaced on Run Explorer 3022 (D6-IA-09).
_IDENTITY_ROW_ORDER: tuple[str, ...] = (
    "run_id",
    "pipeline_name",
    "run_type",
    "status",
    "started_at",
    "completed_at",
    "duration_seconds",
    "tracking_coverage",
    "workflow_id",
    "workflow_run_id",
    "workflow_step_id",
    "manifest_id",
    "provider",
    "entity",
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
        "layers": [],
        "failure": [],
        "stage_timings": [],
        "identity_rows": [],
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


def _scalar_or_json(value: object) -> str:
    """Stringify a report field for a Grafana parameter/value table column."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _param_value_rows(
    obj: object,
    *,
    key_order: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    """Turn a JSON object into stable {parameter, value} rows."""
    if not isinstance(obj, dict) or not obj:
        return []
    ordered = [key for key in key_order if key in obj]
    extra = sorted(str(key) for key in obj if key not in key_order)
    return [
        {"parameter": str(key), "value": _scalar_or_json(obj[key])}
        for key in (*ordered, *extra)
    ]


def _table_shape_pipeline_run_report(
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize nested report sections for Grafana Infinity table selectors.

    Object-shaped ``pipeline_run_report_v1`` blocks (reconciliation, layers,
    failure, identity, stage_timings) become lists of {parameter, value} rows
    so table panels do not QUERY_ERROR on a JSON object root_selector.
    """
    shaped = dict(payload)
    recon = payload.get("reconciliation")
    if isinstance(recon, dict):
        shaped["reconciliation"] = _param_value_rows(
            recon, key_order=_RECONCILIATION_ROW_ORDER
        )
    layers = payload.get("layers")
    if isinstance(layers, dict):
        shaped["layers"] = _param_value_rows(layers, key_order=_LAYER_ROW_ORDER)
    elif not isinstance(layers, list):
        shaped["layers"] = []
    failure = payload.get("failure")
    if isinstance(failure, dict):
        shaped["failure"] = _param_value_rows(failure, key_order=_FAILURE_ROW_ORDER)
    elif not isinstance(failure, list):
        shaped["failure"] = []
    timings = payload.get("stage_timings")
    if isinstance(timings, dict):
        shaped["stage_timings"] = _param_value_rows(timings)
    elif not isinstance(timings, list):
        shaped["stage_timings"] = []
    identity = payload.get("identity")
    identity_rows = (
        _param_value_rows(identity, key_order=_IDENTITY_ROW_ORDER)
        if isinstance(identity, dict)
        else []
    )
    coverage = payload.get("tracking_coverage")
    if coverage not in (None, "") and not any(
        row["parameter"] == "tracking_coverage" for row in identity_rows
    ):
        identity_rows.append(
            {"parameter": "tracking_coverage", "value": _scalar_or_json(coverage)}
        )
    shaped["identity_rows"] = identity_rows
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


def _coverage_chip(covers: str) -> str:
    """Map coverage projection to the first-window IN RANGE / OUT OF RANGE chip."""
    if covers == "yes":
        return "IN RANGE"
    if covers in {"outside", "partial"}:
        return "OUT OF RANGE"
    return "UNKNOWN"


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
    coverage_chip = _coverage_chip(covers)
    summary_row = {
        "run_id": run_id,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "gold_records_out": str(gold_out),
        "excluded_by_contract": str(excluded),
        "covers_selected_run": covers,
        "coverage_chip": coverage_chip,
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
