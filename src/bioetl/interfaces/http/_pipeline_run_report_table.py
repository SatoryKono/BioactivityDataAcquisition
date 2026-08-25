"""Pipeline run report table shaping for HealthServer / Run Explorer.

Keeps Grafana Infinity table panels (e.g. panel 3015) on stable
parameter/value rows and HTTP 200 empty shells instead of QUERY_ERROR.
"""

from __future__ import annotations

import json

from bioetl.interfaces.http._pipeline_run_report_coverage import (
    _coverage_chip,
    _coverage_fields,
    _padded_range_ms,
    _parse_grafana_ms,
    _parse_iso_to_ms,
)

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
        "timings_and_failure": [],
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


def _section_param_value_rows(
    section: str,
    rows: object,
) -> list[dict[str, str]]:
    """Tag {parameter, value} rows with a stable section for panel 3014."""
    if not isinstance(rows, list):
        return []
    tagged: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or "parameter" not in row:
            continue
        tagged.append(
            {
                "section": section,
                "parameter": str(row["parameter"]),
                "value": _scalar_or_json(row.get("value")),
            }
        )
    return tagged


def _shape_object_or_list_block(
    payload: dict[str, object],
    shaped: dict[str, object],
    key: str,
    *,
    key_order: tuple[str, ...] = (),
) -> None:
    """Project an object block to param/value rows; keep lists; else empty list."""
    value = payload.get(key)
    if isinstance(value, dict):
        shaped[key] = _param_value_rows(value, key_order=key_order)
        return
    if not isinstance(value, list):
        shaped[key] = []


def _removal_label(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    label = str(item.get("reason_code") or item.get("outcome") or "").strip()
    count = item.get("count")
    if not label:
        return ""
    if count in (None, ""):
        return label
    return f"{count} {label}"


def _removals_summary(removals: object) -> str:
    """Compact funnel removals for Grafana (not raw JSON arrays)."""
    if not isinstance(removals, list):
        return "—"
    parts = [_removal_label(item) for item in removals]
    return ", ".join(part for part in parts if part) or "—"


def _shape_funnel_rows(payload: dict[str, object]) -> object:
    """Copy funnel stages and add removals_summary for table display."""
    funnel = payload.get("funnel")
    if not isinstance(funnel, list):
        return []
    shaped_rows: list[object] = []
    for stage in funnel:
        if not isinstance(stage, dict):
            shaped_rows.append(stage)
            continue
        row = dict(stage)
        row["removals_summary"] = _removals_summary(stage.get("removals"))
        shaped_rows.append(row)
    return shaped_rows


def _shape_identity_rows(payload: dict[str, object]) -> list[dict[str, str]]:
    """Build identity_rows, including tracking_coverage when not already present."""
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
    return identity_rows


def _table_shape_pipeline_run_report(
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize nested report sections for Grafana Infinity table selectors.

    Object-shaped ``pipeline_run_report_v1`` blocks (reconciliation, layers,
    failure, identity, stage_timings) become lists of {parameter, value} rows
    so table panels do not QUERY_ERROR on a JSON object root_selector.

    ``failure``, ``stage_timings``, ``identity_rows``, ``layers``, and
    ``timings_and_failure`` are always lists. Infinity JSONata ``root_selector``
    errors when the key is missing (#9373); an empty array is VALID EMPTY.
    """
    shaped = dict(payload)
    recon = payload.get("reconciliation")
    if isinstance(recon, dict):
        shaped["reconciliation"] = _param_value_rows(
            recon, key_order=_RECONCILIATION_ROW_ORDER
        )
    _shape_object_or_list_block(payload, shaped, "layers", key_order=_LAYER_ROW_ORDER)
    _shape_object_or_list_block(
        payload, shaped, "failure", key_order=_FAILURE_ROW_ORDER
    )
    _shape_object_or_list_block(payload, shaped, "stage_timings")
    shaped["identity_rows"] = _shape_identity_rows(payload)
    shaped["funnel"] = _shape_funnel_rows(payload)
    shaped["timings_and_failure"] = [
        *_section_param_value_rows("failure", shaped.get("failure")),
        *_section_param_value_rows("stage_timings", shaped.get("stage_timings")),
    ]
    return shaped


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
