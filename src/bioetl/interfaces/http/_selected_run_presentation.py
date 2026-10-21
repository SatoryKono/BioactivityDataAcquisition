"""Grafana presentation of exact-run evidence without changing canonical verdicts."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlencode

_SELECT_RUN = "SELECT RUN"


def presentation_rows(
    rows: list[dict[str, object]], *, selection: bool = False
) -> list[dict[str, object]]:
    """Keep canonical domain verdicts intact; present one neutral selection action."""
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
                "action_path": "d/bioetl-run-explorer-v1/run-explorer?var-run_id=-",
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
