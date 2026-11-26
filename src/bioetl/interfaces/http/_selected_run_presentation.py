"""Grafana presentation of exact-run evidence without changing canonical verdicts."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlencode

from bioetl.application.observability.reason_aliases import display_reason
from bioetl.domain.run_reports.selected_status import (
    provider_check_rows,
    provider_selector_options,
)
from bioetl.domain.run_reports.stage_diagnostics import project_stage_diagnostics
from bioetl.interfaces.http._selected_run_report_assessment import _saved_trust

_CONTROL_PLANE = "Control Plane"
_SELECT_RUN = "SELECT RUN"
_NO_RUNS = "NO RUNS"
_RUN_EXPLORER_SELECT_PATH = "d/bioetl-run-explorer-v1/1-run-explorer?var-run_id=-"


def presentation_rows(
    rows: list[dict[str, object]],
    *,
    selection: bool = False,
    empty_catalog: bool = False,
) -> list[dict[str, object]]:
    """Keep canonical domain verdicts intact; present one neutral selection action."""
    if empty_catalog:
        return [
            {
                **(rows[0] if rows else {}),
                "domain": "Selected run",
                "execution_state": _NO_RUNS,
                "evidence_completeness": _NO_RUNS,
                "run_verdict": _NO_RUNS,
                "verdict": _NO_RUNS,
                "reason": "no_runs_in_scope",
                "action": "No runs in current scope",
                "action_path": _RUN_EXPLORER_SELECT_PATH,
            }
        ]
    if selection:
        return [
            {
                **(rows[0] if rows else {}),
                "domain": "Selected run",
                "execution_state": _SELECT_RUN,
                "evidence_completeness": _SELECT_RUN,
                "run_verdict": _SELECT_RUN,
                "verdict": _SELECT_RUN,
                "reason": "Choose a run to inspect saved evidence",
                "action": "Choose a run",
                "action_path": _RUN_EXPLORER_SELECT_PATH,
            }
        ]
    return [
        {
            **row,
            "action_path": (
                "api/datasources/proxy/uid/bioetl-ops-http/ops/observability/"
                "pipeline-run-report-artifact?"
                + urlencode(
                    {
                        "pipeline": str(row.get("pipeline", "")),
                        "run_id": str(row.get("run_id", "")),
                        "format": "pipeline_run_report_json",
                    }
                )
            ),
        }
        for row in rows
    ]


_UNKNOWN_CHECK_LABELS = {
    "manifest_not_recorded": "manifest for this run was not recorded",
}


def _check_labels(value: object, *, translate: bool = False) -> str:
    """Render a recorded check list, preserving its empty marker."""
    if not isinstance(value, list) or not value:
        return "—"
    if translate:
        return ", ".join(
            _UNKNOWN_CHECK_LABELS.get(str(code), str(code)) for code in value
        )
    return ", ".join(value)


def _readiness_fields(projection: Mapping[str, object]) -> dict[str, object]:
    blocker_text = _check_labels(projection.get("blockers"))
    unknown_text = _check_labels(projection.get("unknown_checks"), translate=True)
    row = {
        key: value
        for key, value in projection.items()
        if key not in {"checks", "blockers", "unknown_checks"}
    }
    row["blockers"] = blocker_text
    row["unknown_checks"] = unknown_text
    explanations = []
    if blocker_text != "—":
        explanations.append("Failed checks: " + blocker_text)
    if unknown_text != "—":
        explanations.append("Not verified: " + unknown_text)
    row["explanation"] = "; ".join(explanations) or (
        "Required replay checks passed"
        if projection.get("verdict") == "READY"
        else "Open replay checks for the assessment basis"
    )
    checks = projection.get("checks")
    return {
        "replay_readiness": [row],
        "replay_checks": checks if isinstance(checks, list) else [],
    }


def _assessment_summary(
    report: Mapping[str, object],
    identity: Mapping[str, object],
    assessment: Mapping[str, object],
    availability: str,
    revision: str,
    pipeline: str,
    run_id: str,
    *,
    heartbeat_now: str,
) -> dict[str, object]:
    """Project the saved assessment identity before probing current artifacts."""
    return {
        **{key: value for key, value in assessment.items() if key != "domains"},
        "pipeline": pipeline,
        "run_id": run_id,
        "completed_at": identity.get("completed_at"),
        "run_type": identity.get("run_type"),
        "workflow_id": identity.get("workflow_id"),
        "started_at": identity.get("started_at"),
        "evaluation_at": report.get("assessment_at", identity.get("completed_at")),
        "revision": revision,
        "evidence_availability": availability,
        "heartbeat_now": heartbeat_now,
        "reason": "Saved run evidence; CURRENT and chart coverage are separate",
    }


def present_saved_status(
    summary: dict[str, object],
    report: dict[str, object],
    domain_rows: list[dict[str, object]],
    readiness_fields: dict[str, object],
) -> dict[str, object]:
    """Format domain rows, Trust and presentation mirrors for one saved report."""
    issues = [
        f"{row['domain']}: {display_reason(str(row.get('reason', '')))}"
        for row in domain_rows
        if row.get("verdict") not in {"OK", "N/A"}
    ]
    if issues:
        summary["reason"] = "; ".join(issues)
    rows = [
        {
            **summary,
            **row,
            "run_verdict": summary["verdict"],
            "display_verdict": row["verdict"],
            "reason_display": display_reason(str(row.get("reason", ""))),
        }
        for row in domain_rows
    ]
    trust = _saved_trust(report, summary, rows)
    for row in rows:
        if row["domain"] == _CONTROL_PLANE:
            row["reason_display"] = trust["reasons_display"] or "No saved Trust reasons"
            row["display_verdict"] = trust["trust_status"]
    return {
        **summary,
        "summary": [summary],
        "presentation_summary": [summary],
        "presentation_trust": [trust],
        "domains": rows,
        "presentation_domains": presentation_rows(rows),
        "provider_checks": provider_check_rows(report),
        "provider_options": provider_selector_options(report),
        "quality_evidence": {
            "pipeline": summary["pipeline"],
            "funnel": report.get("funnel"),
        },
        "rows": rows,
        "trust": [trust],
        **readiness_fields,
        **project_stage_diagnostics(report),
    }
